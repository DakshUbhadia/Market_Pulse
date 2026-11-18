"""Refresh, validate, rank and freeze unseen local paper signals; never publish."""
from quant.identity.transitions import TRANSITION_VERSION
from dataclasses import asdict
from datetime import datetime, timezone
from datetime import date
import json
from pathlib import Path

import pandas as pd

from quant.backtest.costs import CostModel
from quant.backtest.portfolio import PortfolioConfig
from quant.forward.gate import require_completed_baselines
from quant.forward.signal_store import append_record, content_hash, freeze_signals, read_signals
from quant.forward.shadow_portfolio import update_shadow
from quant.forward.metrics import forward_metrics
from quant.forward.calendar import next_session_open
from quant.identity.transitions import load_transitions
from quant.forward.cohort import cohort_root, cohort_report
from quant.lifecycle.policy import DEFAULT_LIFECYCLE_SCENARIO
from quant.lifecycle.state import simulation_time
from quant.pipeline.backfill_lifecycle import load_lifecycle
from quant.pipeline.check_research_ready import require_research_ready
from quant.pipeline.update_calendar import read_calendar
from quant.storage.duckdb_store import query_dataset
from quant.storage.research_store import load_research_data, write_json, verify_manifest, digest_file
from quant.version import COST_MODEL_VERSION, EVIDENCE_POLICY_VERSION
from quant.boundaries import RAW_PRICE_START


def run_forward_signal(config, as_of, *, price_baseline, total_return_baseline, refresh=True, now=None, cohort=None):
    root = cohort_root(config,cohort)
    supplied_time = now is not None
    now = pd.Timestamp(now or datetime.now(timezone.utc))
    baselines = require_completed_baselines(config,price_baseline,total_return_baseline)
    if any(item['date_range']['to'] > str(as_of) for item in baselines.values()):
        raise ValueError('Baseline must end before forward decisions')
    if refresh:
        from quant.pipeline.update_all import update_all
        report = update_all(config,as_of,as_of,incremental=True)
        if report['status'] != 'READY':
            raise ValueError('Daily data refresh is not ready; inspect data health')
    calendar = read_calendar(config, RAW_PRICE_START, as_of)
    sessions = pd.DatetimeIndex(calendar.loc[calendar.is_trading_session,'trade_date'])
    if pd.Timestamp(as_of) not in sessions:
        raise ValueError('Forward as_of must be a dated exchange session')
    next_open, session_evidence = next_session_open(config,as_of)
    if now.tzinfo is None or not simulation_time(as_of,'15:30') <= now < next_open:
        raise ValueError('Historical or premature signals cannot be labelled forward evidence')
    require_research_ready(config,as_of)
    portfolio, costs = PortfolioConfig(), CostModel()
    settings = dict(security_transition_version=TRANSITION_VERSION,portfolio=asdict(portfolio), costs=asdict(costs), cost_model_version=COST_MODEL_VERSION,
        evidence_policy_version=EVIDENCE_POLICY_VERSION, lifecycle_scenario=DEFAULT_LIFECYCLE_SCENARIO,
        return_basis='TOTAL_RETURN', baselines=baselines)
    signal_path = root/'signals'/f'{as_of}.json'
    if not signal_path.exists():
        from quant.pipeline.build_features import build_features
        from quant.pipeline.run_factor_v1 import run_factor_v1
        _, feature_path = build_features(config,as_of)
        scores,_ = run_factor_v1(config,as_of)
        manifest = json.loads(feature_path.with_suffix('.manifest.json').read_text(encoding='utf-8'))
        verify_manifest(config,manifest)
        if digest_file(feature_path) != manifest['feature_sha256']:
            raise ValueError('Feature artifact changed before signal freeze')
        manifest_hash = content_hash(manifest)
        append_record(root/'sources'/f'{manifest_hash}.json',manifest)
        signal_path = freeze_signals(root,scores,as_of=as_of,
            generated_at=now if supplied_time else datetime.now(timezone.utc),data_as_of=as_of,
            git_commit=manifest['git_commit'],source_manifest_hash=manifest_hash,next_open=next_open,
            next_session_evidence=session_evidence,settings=settings)
    else:
        batches,_ = read_signals(root)
        existing = next(batch for batch in batches if batch['as_of'] == str(as_of))
        if existing['settings'] != json.loads(json.dumps(settings,default=str)):
            raise ValueError('Paper portfolio settings differ from frozen signal settings')
    prices,benchmark,sessions,_,_ = load_research_data(config,as_of)
    actions = query_dataset(config.data_dir,'corporate_actions',end=as_of).drop_duplicates('event_id')
    events = load_lifecycle(config)
    shadow = update_shadow(root,prices,sessions,as_of=as_of,portfolio=portfolio,cost_model=costs,
        corporate_actions=actions,lifecycle_events=events,lifecycle_scenario=DEFAULT_LIFECYCLE_SCENARIO,
        security_transitions=load_transitions(config),transition_data_dir=config.data_dir)
    from quant.pipeline.update_forward_outcomes import update_forward_outcomes
    outcomes = update_forward_outcomes(config,as_of,**({'cohort':cohort} if cohort is not None else {}))
    result = dict(status='BLOCKED' if outcomes['blocked'] else 'PAPER_ONLY',signals=str(signal_path),
        shadow=str(shadow),outcomes=outcomes,metrics=forward_metrics(root),public_recommendations_allowed=False)
    write_json(cohort_report(config,cohort,'forward-paper.json'),result)
    return result


def main():
    from quant.pipeline.cli import parser_config
    parser,config = parser_config(__doc__)
    parser.add_argument('--as-of',required=True,type=date.fromisoformat)
    parser.add_argument('--price-baseline',required=True,type=Path)
    parser.add_argument('--total-return-baseline',required=True,type=Path)
    parser.add_argument('--skip-data-update',action='store_true',help='Use data already acquired by the daily pipeline')
    parser.add_argument('--cohort',help='New name when policy or portfolio settings change; existing cohorts stay immutable')
    args = parser.parse_args()
    config = args.config(config)
    try:
        result = run_forward_signal(config,args.as_of,price_baseline=args.price_baseline,
            total_return_baseline=args.total_return_baseline,refresh=not args.skip_data_update,cohort=args.cohort)
    except (OSError,ValueError,KeyError) as error:
        result = dict(status='BLOCKED',reason=str(error),production_validated=False)
        write_json(config.data_dir/'reports/forward-paper.json',result)
    print(json.dumps(result,indent=2,default=str))
    return 1 if result['status'] == 'BLOCKED' else 0


if __name__ == '__main__':
    raise SystemExit(main())
