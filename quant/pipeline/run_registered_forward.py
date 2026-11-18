"""Collect registered V1/V2 paper cohorts at real after-close decision times."""
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
import json
import re
import pandas as pd

from quant.backtest.costs import CostModel
from quant.backtest.portfolio import PortfolioConfig
from quant.features.matrix import build_feature_matrix
from quant.forward.calendar import next_session_open
from quant.forward.gate import require_completed_baselines
from quant.forward.signal_store import append_record, content_hash, freeze_signals
from quant.forward.shadow_portfolio import update_shadow
from quant.forward.outcome_tracker import track_outcomes
from quant.models.registry import ModelRegistry
from quant.models.factor_v1 import score_factor_v1
from quant.models.factor_v2 import same_universe_scores
from quant.pipeline.backfill_lifecycle import load_lifecycle
from quant.pipeline.check_research_ready import require_research_ready
from quant.pipeline.build_fundamental_features import build_fundamental_features
from quant.pipeline.audit_fundamental_coverage import verify_filing_archives
from quant.identity.transitions import load_transitions, TRANSITION_VERSION
from quant.lifecycle.policy import DEFAULT_LIFECYCLE_SCENARIO
from quant.lifecycle.state import simulation_time
from quant.storage.research_store import input_manifest, load_research_data, write_json, digest_file, verify_manifest
from quant.storage.parquet_store import read_parquet_file
from quant.storage.duckdb_store import query_dataset
from quant.version import MODEL_VERSION, EVIDENCE_POLICY_VERSION, COST_MODEL_VERSION


def run_registered_forward(config, *, registry, model_id, cohort, as_of, price_baseline,
                           total_return_baseline, spec_path=None, fundamental_paths=None, now=None):
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,63}', cohort):
        raise ValueError('A simple named forward cohort is required')
    store = ModelRegistry(registry)
    card = store.require_forward_candidate(model_id)
    root = config.data_dir/'forward/registered'/model_id/cohort
    baselines = require_completed_baselines(config, price_baseline, total_return_baseline)
    if any(r['date_range']['to'] >= str(as_of) for r in baselines.values()):
        raise ValueError('Historical baseline must precede the real forward signal date')
    generated = pd.Timestamp(now or datetime.now(timezone.utc))
    opening, session_evidence = next_session_open(config, as_of)
    if generated.tzinfo is None or not simulation_time(as_of, '15:30') <= generated < opening:
        raise ValueError('Forward evidence must be collected after close and before the next open')
    require_research_ready(config, as_of)
    manifest = input_manifest(config, as_of)
    prices, benchmark, sessions, delivery, _ = load_research_data(config, as_of)
    if pd.Timestamp(as_of) not in pd.DatetimeIndex(sessions):
        raise ValueError('Forward as_of must be a certified exchange session')
    lifecycle = load_lifecycle(config)
    features = build_feature_matrix(prices, benchmark, sessions, delivery=delivery, eligible_only=True, lifecycle_events=lifecycle)
    features = features[pd.to_datetime(features.as_of).eq(pd.Timestamp(as_of))]
    extra_hashes = {}
    portfolio, costs = PortfolioConfig(), CostModel()
    if card['model_version'] == MODEL_VERSION:
        scores = score_factor_v1(features)
    else:
        from quant.research.specification import load_specification
        if not spec_path or not fundamental_paths or len(fundamental_paths) != 4:
            raise ValueError('V2 forward requires its frozen spec and PIT filing/share inputs')
        spec = load_specification(spec_path)
        if content_hash(spec) != card['spec_hash']:
            raise ValueError('Forward specification differs from historically validated model card')
        if spec['portfolio'] != asdict(portfolio):
            raise ValueError('Initial cohorts require comparable V1/V2 portfolio capital and execution rules')
        extra_hashes = {str(p): digest_file(p) for p in [spec_path, *fundamental_paths]}
        filings, anchors, events, coverage = [read_parquet_file(p) for p in fundamental_paths]
        from quant.pipeline.audit_share_history_coverage import verify_share_archives
        anchors, events, coverage = [verify_share_archives(f, config.data_dir) for f in (anchors, events, coverage)]
        filings = verify_filing_archives(filings, config.data_dir)
        raw = prices.loc[pd.to_datetime(prices.trade_date).eq(pd.Timestamp(as_of)), ['instrument_id', 'raw_close']]
        keys = features[['as_of', 'instrument_id']].merge(raw, on='instrument_id', validate='one_to_one')
        fundamentals = build_fundamental_features(keys, filings, anchors, events, coverage)
        scores = same_universe_scores(features, fundamentals, min_group_size=spec['min_group_size'])['factor_v2']
        liquid = features.sort_values(['adv60', 'instrument_id'], ascending=[False, True]).head(100)
        if (features.empty or liquid.empty or len(scores)/len(features) < .8
                or liquid.instrument_id.isin(scores.instrument_id).mean() < .9):
            raise ValueError('Forward V2 cutoff fails PIT feature coverage')
        scores['feature_version'] = card['feature_version']
    settings = dict(model_card_sha256=card['sha256'], model_id=model_id, portfolio=asdict(portfolio),
        costs=asdict(costs), cost_model_version=COST_MODEL_VERSION, security_transition_version=TRANSITION_VERSION,
        evidence_policy_version=EVIDENCE_POLICY_VERSION, lifecycle_scenario=DEFAULT_LIFECYCLE_SCENARIO,
        return_basis='TOTAL_RETURN', baselines=baselines)
    verify_manifest(config, manifest)
    if extra_hashes != {str(p): digest_file(p) for p in extra_hashes}:
        raise ValueError('PIT inputs changed during forward feature construction')
    manifest['additional_input_sha256'] = extra_hashes
    manifest_hash = content_hash(manifest)
    append_record(root/'sources'/f'{manifest_hash}.json', manifest)
    path = freeze_signals(root, scores, as_of=as_of, data_as_of=as_of,
        generated_at=generated if now is not None else datetime.now(timezone.utc),
        git_commit=manifest['git_commit'], source_manifest_hash=manifest_hash,
        next_open=opening, next_session_evidence=session_evidence, settings=settings, model_card=card)
    actions = query_dataset(config.data_dir, 'corporate_actions', end=as_of).drop_duplicates('event_id')
    transitions = load_transitions(config)
    shadow = update_shadow(root, prices, sessions, as_of=as_of, portfolio=portfolio, cost_model=costs,
        corporate_actions=actions, lifecycle_events=lifecycle, lifecycle_scenario=DEFAULT_LIFECYCLE_SCENARIO,
        security_transitions=transitions, transition_data_dir=config.data_dir, model_card=card)
    tri = query_dataset(config.data_dir, 'index_tri', end=as_of)
    outcomes = track_outcomes(root, prices, benchmark, tri[tri.index_name.eq('NIFTY 500 TRI')], sessions,
        as_of=as_of, cost_model=costs, corporate_actions=actions, lifecycle_events=lifecycle,
        lifecycle_scenario=DEFAULT_LIFECYCLE_SCENARIO, security_transitions=transitions, transition_data_dir=config.data_dir)
    report = dict(status='REVIEW_REQUIRED' if outcomes['blocked'] else 'PAPER_ONLY',
        root=str(root), signal=str(path), shadow=str(shadow), outcomes=outcomes,
        model_card_sha256=card['sha256'], public_recommendations_allowed=False)
    write_json(root/'reports/forward.json', report)
    return report


def main():
    from datetime import date
    from quant.pipeline.cli import parser_config
    parser, config = parser_config(__doc__)
    for name in ('registry', 'price-baseline', 'total-return-baseline', 'spec', 'filings', 'anchors', 'capital-events', 'share-coverage'):
        parser.add_argument('--'+name, type=Path, required=name in ('registry', 'price-baseline', 'total-return-baseline'))
    parser.add_argument('--model-id', required=True)
    parser.add_argument('--cohort', required=True)
    parser.add_argument('--as-of', required=True, type=date.fromisoformat)
    args = parser.parse_args()
    report = run_registered_forward(args.config(config), registry=args.registry, model_id=args.model_id,
        cohort=args.cohort, as_of=args.as_of, price_baseline=args.price_baseline, total_return_baseline=args.total_return_baseline,
        spec_path=args.spec, fundamental_paths=[args.filings, args.anchors, args.capital_events, args.share_coverage]
        if all([args.filings, args.anchors, args.capital_events, args.share_coverage]) else None)
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
