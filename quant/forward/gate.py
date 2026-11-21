"""Paper collection requires complete frozen price and total-return experiments."""
import json
from pathlib import Path

from quant.identity.transitions import TRANSITION_VERSION
from quant.storage.research_store import digest_file
from quant.backtest.artifacts import verify_backtest_seal
from quant.backtest.costs import CostModel
from quant.backtest.portfolio import PortfolioConfig
from quant.storage.research_store import clean_json
from quant.version import (MODEL_VERSION, FEATURE_VERSION, EVIDENCE_POLICY_VERSION,
                           LIFECYCLE_POLICY_VERSION, PORTFOLIO_ACCOUNTING_VERSION, COST_MODEL_VERSION)


def require_completed_baselines(config, price_baseline, total_return_baseline):
    from quant.governance.gates import require_action
    require_action(config, 'V1_FORWARD')
    output = {}
    expected_costs = clean_json(vars(CostModel()))
    expected_costs.pop('allow_estimated_history')
    for basis, folder in [('PRICE',price_baseline),('TOTAL_RETURN',total_return_baseline)]:
        path = Path(folder)
        verify_backtest_seal(path)
        manifest = json.loads((path/'config.json').read_text(encoding='utf-8'))
        required = ('metrics.json','ic.parquet','deciles.parquet','robustness.json','benchmarks.json',
                    'equity_curve.parquet','holdings.parquet','trades.parquet','lifecycle.parquet',
                    'baseline-comparison.json','cluster-exposure.json','IC-confidence-interval.json',
                    'v1-decision.json','lifecycle-audit.json','security-transitions.parquet',
                    'cluster-sensitivity.parquet','skipped_orders.parquet','rolling_excess.parquet','dividends.parquet')
        if any(not (path/name).is_file() for name in required) or not list((path/'walk_forward').glob('*/run-*/metrics.json')):
            raise ValueError('Forward paper testing requires complete frozen baseline artifacts')
        if manifest.get('date_range',{}).get('from','9999') > '2016-01-01':
            from quant.research.evaluation_window import load_evaluation_window
            window = load_evaluation_window(path/'evaluation-window.json')
            if (not window['blocking_event_ids'] or window['requested_start'] != '2016-01-01'
                    or window['effective_start'] != manifest['date_range']['from']
                    or window != manifest.get('evaluation_window')):
                raise ValueError('Later baseline requires the same predeclared evidence-exhaustion window')
        if (manifest.get('return_basis') != basis
                or manifest.get('model_version') != MODEL_VERSION or manifest.get('feature_version') != FEATURE_VERSION
                or manifest.get('security_transition_version') != TRANSITION_VERSION
                or manifest.get('evidence_policy_version') != EVIDENCE_POLICY_VERSION
                or manifest.get('cost_model_version') != COST_MODEL_VERSION
                or manifest.get('lifecycle_policy_version') != LIFECYCLE_POLICY_VERSION
                or manifest.get('lifecycle_scenario') != 'MANDATORY_ECONOMIC_EVENTS_ONLY'
                or (basis == 'TOTAL_RETURN' and manifest.get('portfolio_accounting_version') != PORTFOLIO_ACCOUNTING_VERSION)):
            raise ValueError('Frozen baseline does not match the unchanged current V1 baseline policy')
        from quant.storage.duckdb_store import dataset_files
        current_transitions={str(Path(p).relative_to(config.data_dir)):digest_file(p)
            for p in dataset_files(config.data_dir,'security_transitions')}
        frozen_transitions={r['path']:r['sha256'] for r in manifest.get('files',[])
            if r['path'].replace('\\','/').startswith('normalized/security_transitions/')}
        if current_transitions != frozen_transitions:
            raise ValueError('Transition evidence differs from the sealed baseline')
        baseline_costs = dict(manifest.get('cost_settings', {}))
        baseline_costs.pop('allow_estimated_history', None)
        if (manifest.get('portfolio_settings') != clean_json(PortfolioConfig())
                or baseline_costs != expected_costs):
            raise ValueError('Paper sizing or costs differ from the frozen historical baseline')
        stress = json.loads((path/'robustness.json').read_text(encoding='utf-8'))
        if not {'cost_1_5x','cost_2x'} <= set(stress):
            raise ValueError('Frozen baseline requires cost stress evidence')
        decision = json.loads((path/'v1-decision.json').read_text(encoding='utf-8'))
        if decision.get('decision') != 'GO_FURTHER_V1_RESEARCH':
            raise ValueError('V1 go/no-go decision blocks forward launch; investigate before proceeding')
        lifecycle = json.loads((path/'lifecycle-audit.json').read_text(encoding='utf-8'))
        if (lifecycle.get('status') == 'BLOCKED' or lifecycle.get('held_event_assessment') != 'ASSESSED'
                or lifecycle.get('held_events_unresolved') != 0):
            raise ValueError('Unresolved or unassessed held lifecycle events block forward launch')
        evidence = json.loads((path/'metrics.json').read_text(encoding='utf-8'))['evidence']
        output[basis] = dict(path=str(path.resolve()),completion_sha256=digest_file(path/'completion.json'),date_range=manifest['date_range'],
            evidence_status=evidence['status'], highest_validation_level=evidence.get('highest_validation_level','NOT_VALIDATED'),
            evaluation_window=manifest.get('evaluation_window'))
    if output['PRICE']['date_range'] != output['TOTAL_RETURN']['date_range']:
        raise ValueError('Frozen price and total-return baselines must cover the same date range')
    if output['PRICE'].get('evaluation_window') != output['TOTAL_RETURN'].get('evaluation_window'):
        raise ValueError('Both return bases must share the same predeclared evaluation window')
    return output
