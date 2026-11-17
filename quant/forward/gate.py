"""Paper collection requires complete frozen price and total-return experiments."""
import json
from pathlib import Path

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
                    'baseline-comparison.json','cluster-exposure.json','IC-confidence-interval.json')
        if any(not (path/name).is_file() for name in required) or not list((path/'walk_forward').glob('*/run-*/metrics.json')):
            raise ValueError('Forward paper testing requires complete frozen baseline artifacts')
        if (manifest.get('return_basis') != basis or manifest.get('date_range',{}).get('from','9999') > '2016-01-01'
                or manifest.get('model_version') != MODEL_VERSION or manifest.get('feature_version') != FEATURE_VERSION
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
        evidence = json.loads((path/'metrics.json').read_text(encoding='utf-8'))['evidence']
        output[basis] = dict(path=str(path.resolve()),date_range=manifest['date_range'],
            evidence_status=evidence['status'], highest_validation_level=evidence.get('highest_validation_level','NOT_VALIDATED'))
    return output
