"""Exercise draft four-arm V2 software without baselines, freezing or model decisions."""
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4
import json

import pandas as pd

from quant.backtest.portfolio import PortfolioConfig
from quant.backtest.costs import CostModel
from quant.backtest.artifacts import complete_diagnostic
from quant.governance.gates import GateRegistry, GATE_ID
from quant.forward.signal_store import append_record, content_hash
from quant.pipeline.prepare_v2_matrix import prepare_v2_matrix
from quant.pipeline.certify_implementation import require_certified_implementation
from quant.portfolio.constraints import RiskPolicy
from quant.research.multifactor import compare_models
from quant.research.capacity import capacity_scenarios
from quant.research.factor_evidence import factor_evidence
from quant.research.specification import research_code_hashes
from quant.storage.parquet_store import read_parquet_file, write_parquet
from quant.storage.research_store import digest_file, write_json, git_commit


def run_v2_diagnostics(config, *, prices, price_features, fundamental_features, labels,
                       benchmark, sessions, draft_spec, input_scope, input_files=()):
    if input_scope not in ('SYNTHETIC_CONTROLLED_INPUTS', 'ARCHIVED_DIAGNOSTIC_INPUTS'):
        raise ValueError('Declare the controlled diagnostic input scope')
    if draft_spec.get('review_status') != 'DRAFT':
        raise ValueError('Diagnostic V2 must use an explicitly DRAFT specification')
    if draft_spec.get('capacity_scenarios') != [1_000_000, 2_500_000, 5_000_000, 10_000_000]:
        raise ValueError('Diagnostic V2 exercises all four predeclared capital scenarios')
    folder = config.data_dir/'artifacts/diagnostics/factor_v2'/(
        datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')+'-'+uuid4().hex[:8])
    folder.mkdir(parents=True, exist_ok=False)
    gates = GateRegistry(config.data_dir).require('DIAGNOSTIC_V2')
    context = dict(research_authority='DIAGNOSTIC_ONLY', seal_eligible=False, historical_validation=False,
        promotion_eligible=False, real_forward_evidence=False, governance_gate=GATE_ID,
        governance_status=gates['human_review_status'], input_scope=input_scope)
    append_record(folder/'diagnostic-authority.json', context)
    code, hashes = research_code_hashes(), {str(p): digest_file(p) for p in input_files}
    try:
        certificate = require_certified_implementation(config)
        ranked, matrix_status = prepare_v2_matrix(price_features, fundamental_features,
                                                   min_group_size=draft_spec['min_group_size'])
        write_json(folder/'matrix-status.json', matrix_status)
        if matrix_status['status'] != 'COMPLETE_RESEARCH_INPUTS':
            raise ValueError('Full V2 diagnostic matrix is INCOMPLETE; Value/coverage gates remain required')
        risk_features = price_features[['as_of', 'instrument_id', 'adv60']].copy()
        portfolio, costs = PortfolioConfig(**draft_spec['portfolio']), CostModel(**draft_spec['costs'])
        policy = RiskPolicy(**draft_spec['risk']['constraints'])
        windows = draft_spec['evaluation_windows']
        if (not windows or any(pd.Timestamp(w['from']) > pd.Timestamp(w['to']) for w in windows)
                or any(pd.Timestamp(left['to']) >= pd.Timestamp(right['from'])
                       for left, right in zip(windows, windows[1:]))):
            raise ValueError('Declare ordered diagnostic evaluation dates before execution')
        metrics = {}
        for i, window in enumerate(windows):
            compared, factor_ic = compare_models(prices, ranked, labels, benchmark, sessions, window,
                portfolio=portfolio, cost_model=costs, risk_features=risk_features, risk_policy=policy)
            root = folder/f'window-{i:02d}'
            factors, correlations = factor_evidence(ranked['factor_v2'], labels, window)
            write_json(root/'factor-evidence.json', factors)
            write_parquet(correlations, root/'factor-correlations.parquet')
            write_parquet(factor_ic, root/'factor-ic.parquet')
            for name, row in compared.items():
                arm = root/name
                for key in ('metrics', 'stress', 'risk_evidence', 'risk_budgets'):
                    write_json(arm/(key.replace('_', '-')+'.json'), row[key])
                for field in ('equity_curve', 'trades', 'holdings', 'skipped_orders', 'dividends',
                              'lifecycle', 'security_transitions', 'target_orders'):
                    write_parquet(getattr(row['result'], field), arm/(field.replace('_', '-')+'.parquet'))
                for key in ('ic', 'deciles', 'rolling'):
                    write_parquet(row[key], arm/(key+'.parquet'))
            write_json(root/'capacity-scenarios.json', capacity_scenarios(prices, ranked['factor_v2'],
                risk_features, benchmark, sessions, window, capitals=draft_spec['capacity_scenarios'],
                portfolio=portfolio, costs=costs, policy=policy, execution={}, return_basis='PRICE'))
            metrics[f'window-{i:02d}'] = {name: row['metrics'] for name, row in compared.items()}
        if code != research_code_hashes() or hashes != {str(p): digest_file(p) for p in input_files}:
            raise ValueError('Diagnostic source or input bytes changed')
        write_json(folder/'config.json', dict(context, specification=draft_spec, git_commit=git_commit(),
            source_code_sha256=code, implementation_certification=certificate))
        write_json(folder/'input-manifest.json', dict(input_scope=input_scope, input_sha256=hashes,
            source_code_sha256=code, data_content_sha256=content_hash(matrix_status)))
        write_json(folder/'metrics.json', metrics)
        write_json(folder/'outcome.json', dict(context, status='DIAGNOSTIC_COMPLETE',
            decision='DIAGNOSTIC_ONLY', historical_v2_decision_created=False))
        complete_diagnostic(folder, reason='GOVERNANCE_REVIEW_PENDING'
            if gates['human_review_status'] == 'PENDING' else 'DIAGNOSTIC_ONLY',
            governance_status=gates['human_review_status'])
        return folder
    except Exception as error:
        from quant.research.authority import blocked_outcome
        write_json(folder/'outcome.json', dict(context, status='BLOCKED', outcome=blocked_outcome(error), reason=str(error)))
        raise


def main():
    from quant.pipeline.cli import parser_config
    parser, config = parser_config(__doc__)
    for name in ('prices', 'price-features', 'fundamental-features', 'labels', 'benchmark', 'calendar', 'draft-spec'):
        parser.add_argument('--'+name, type=Path, required=True)
    parser.add_argument('--input-scope', required=True, choices=('SYNTHETIC_CONTROLLED_INPUTS', 'ARCHIVED_DIAGNOSTIC_INPUTS'))
    args = parser.parse_args()
    paths = [args.prices, args.price_features, args.fundamental_features, args.labels, args.benchmark, args.calendar, args.draft_spec]
    frames = [read_parquet_file(p) for p in paths[:-1]]
    calendar = frames[-1]
    sessions = calendar.loc[calendar.is_trading_session, 'trade_date'] if 'is_trading_session' in calendar else calendar.trade_date
    path = run_v2_diagnostics(args.config(config), prices=frames[0], price_features=frames[1],
        fundamental_features=frames[2], labels=frames[3], benchmark=frames[4], sessions=sessions,
        draft_spec=json.loads(args.draft_spec.read_text(encoding='utf-8')), input_scope=args.input_scope, input_files=paths)
    print(path)


if __name__ == '__main__':
    main()
