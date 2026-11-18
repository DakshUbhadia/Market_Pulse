"""Freeze reviewed research policy before evaluating any candidate outcomes."""
from datetime import datetime, timezone
from pathlib import Path
import json

import pandas as pd

from quant.forward.signal_store import append_record, content_hash
from quant.storage.research_store import digest_file
from quant.models.factor_v2 import BLOCKS


def research_code_hashes():
    from quant.config import REPO_ROOT
    return {p.relative_to(REPO_ROOT).as_posix():digest_file(p) for p in (REPO_ROOT/'quant').rglob('*.py')
            if not any(part in ('tests','.venv','__pycache__') for part in p.parts)}


def validate_specification(spec):
    required_policy = {'spec_version', 'feature_definitions', 'normalization', 'missing_data_rules',
                       'coverage_policy', 'portfolio', 'costs', 'risk', 'capacity_scenarios',
                       'training_policy', 'model_version', 'feature_version', 'cost_model_version',
                       'risk_policy_version'}
    if not required_policy.issubset(spec):
        raise ValueError('Specification must freeze feature, coverage, portfolio, cost and risk policies')
    if spec.get('return_basis','PRICE') not in ('PRICE','TOTAL_RETURN'):
        raise ValueError('Unsupported return basis')
    if spec.get('review_status') != 'REVIEWED' or not str(spec.get('reviewed_by') or '').strip():
        raise ValueError('Research specification requires an explicit recorded review')
    if spec.get('block_weights') != {name:1/len(BLOCKS) for name in BLOCKS}:
        raise ValueError('Initial V2 research requires equal declared block weights')
    if spec.get('min_group_size',0)<20:
        raise ValueError('Research normalization needs at least 20 names per entity group')
    windows=spec.get('evaluation_windows',[])
    if not windows:
        raise ValueError('Declare evaluation windows before experiments')
    last=None
    for window in windows:
        start,end=pd.Timestamp(window['from']),pd.Timestamp(window['to'])
        if start>end or (last is not None and start<=last):
            raise ValueError('Evaluation windows must be ordered and nonoverlapping')
        last=end
    required={'min_oos_sessions','min_mean_ic_improvement','min_ir_improvement',
              'max_drawdown_deterioration','max_turnover','min_label_coverage',
              'max_turnover_increase','min_robustness_survival'}
    criteria=spec.get('acceptance',{})
    if set(criteria)!=required or any(not isinstance(v,(int,float)) or not float('-inf')<v<float('inf') for v in criteria.values()):
        raise ValueError('Declare all numerical promotion criteria')
    if (criteria['min_oos_sessions']<504 or min(criteria.values())<0
            or not 0<criteria['min_label_coverage']<=1 or criteria['max_turnover']<=0):
        raise ValueError('Invalid promotion criteria or insufficient declared OOS length')
    from quant.backtest.portfolio import PortfolioConfig
    from quant.backtest.costs import CostModel
    from quant.portfolio.constraints import RiskPolicy
    from quant.version import FACTOR_V2_VERSION, FUNDAMENTAL_FEATURE_VERSION, COST_MODEL_VERSION, PORTFOLIO_RISK_VERSION
    if (spec['model_version'] != FACTOR_V2_VERSION or spec['feature_version'] != FUNDAMENTAL_FEATURE_VERSION
            or spec['cost_model_version'] != COST_MODEL_VERSION or spec['risk_policy_version'] != PORTFOLIO_RISK_VERSION):
        raise ValueError('Candidate policy versions must match the implemented versions')
    PortfolioConfig(**spec['portfolio'])
    CostModel(**spec['costs'])
    RiskPolicy(**spec['risk']['constraints'])
    policy = spec['coverage_policy']
    if (policy.get('minimum_consecutive_months', 0) < 12 or policy.get('overall', 0) < .8
            or policy.get('top100', 0) < .9 or policy.get('overall', 0) > 1 or policy.get('top100', 0) > 1):
        raise ValueError('Coverage policy requires 12 monthly cutoffs and at least 80% / 90% coverage')
    if policy['overall'] != .8 or policy['top100'] != .9:
        raise ValueError('Initial V2 coverage uses the declared 80% / 90% engineering policy')
    from quant.config import REPO_ROOT
    definitions = json.loads((REPO_ROOT/'quant/specs/factor_v2_1.0.0.json').read_text(encoding='utf-8'))
    if any(spec[k] != definitions[k] for k in ('feature_definitions', 'normalization', 'missing_data_rules', 'training_policy')):
        raise ValueError('Frozen feature policy must describe the implemented V2 formulas and PIT rules')
    if not 0 < criteria['min_robustness_survival'] <= 1:
        raise ValueError('Declare a valid robustness survival fraction')
    if not spec['capacity_scenarios'] or any(not isinstance(v, (int, float)) or not 0 < v < float('inf') for v in spec['capacity_scenarios']):
        raise ValueError('Declare positive capital research scenarios')
    if not spec['normalization'] or not spec['missing_data_rules'] or not spec['feature_definitions']:
        raise ValueError('Feature definitions and missing-data/normalization rules cannot be empty')
    return spec


def freeze_specification(spec, output):
    validate_specification(spec)
    # One version has one policy in a specification store. Re-evaluation requires
    # the same frozen record; policy edits require a new spec_version.
    import re
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,95}', spec['spec_version']):
        raise ValueError('Invalid specification version')
    output = Path(output)
    append_record(output.parent/'.specification-versions'/f'{spec["spec_version"]}.json',
        dict(specification_sha256=content_hash(spec), source_code_sha256=research_code_hashes()))
    body=dict(specification=spec,source_code_sha256=research_code_hashes(),
              frozen_at=datetime.now(timezone.utc).isoformat())
    append_record(output,dict(**body,sha256=content_hash(body)))


def load_specification(path):
    record=json.loads(Path(path).read_text())
    if record.get('sha256')!=content_hash({k:v for k,v in record.items() if k!='sha256'}):
        raise ValueError('Frozen specification checksum changed')
    if record['source_code_sha256']!=research_code_hashes():
        raise ValueError('Research implementation changed after specification freeze; review a new specification')
    return validate_specification(record['specification'])
