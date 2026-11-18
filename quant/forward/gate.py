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
                    'v1-decision.json','lifecycle-audit.json','security_transitions.parquet')
        if any(not (path/name).is_file() for name in required) or not list((path/'walk_forward').glob('*/run-*/metrics.json')):
            raise ValueError('Forward paper testing requires complete frozen baseline artifacts')
        if (manifest.get('return_basis') != basis or manifest.get('date_range',{}).get('from','9999') > '2016-01-01'
                or manifest.get('model_version') != MODEL_VERSION or manifest.get('feature_version') != FEATURE_VERSION
                or manifest.get('security_transition_version') != TRANSITION_VERSION
                or manifest.get('evidence_policy_version') != EVIDENCE_POLICY_VERSION
                or manifest.get('cost_model_version') != COST_MODEL_VERSION
                or manifest.get('lifecycle_policy_version') != LIFECYCLE_POLICY_VERSION
                or manifest.get('lifecycle_scenario') != 'MANDATORY_ECONOMIC_EVENTS_ONLY'
                or (basis == 'TOTAL_RETURN' and manifest.get('portfolio_accounting_version') != PORTFOLIO_ACCOUNTING_VERSION)):
            raise ValueError('Frozen baseline does not match the unchanged current V1 baseline policy')
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
            evidence_status=evidence['status'], highest_validation_level=evidence.get('highest_validation_level','NOT_VALIDATED'))
    if output['PRICE']['date_range'] != output['TOTAL_RETURN']['date_range']:
        raise ValueError('Frozen price and total-return baselines must cover the same date range')
    return output
