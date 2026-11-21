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
              'max_turnover_increase','min_robustness_survival', 'min_mean_ic', 'min_ir', 'min_valid_windows'}
    criteria=spec.get('acceptance',{})
    if set(criteria)!=required or any(not isinstance(v,(int,float)) or not float('-inf')<v<float('inf') for v in criteria.values()):
        raise ValueError('Declare all numerical promotion criteria')
    if (criteria['min_oos_sessions']<504 or min(criteria.values())<0
            or not 0<criteria['min_label_coverage']<=1 or criteria['max_turnover']<=0):
        raise ValueError('Invalid promotion criteria or insufficient declared OOS length')
    if type(criteria['min_valid_windows']) is not int or criteria['min_valid_windows'] < 1:
        raise ValueError('Declare a positive minimum number of valid windows')
    if (spec.get('evaluation_dates_selected_using') != 'CERTIFIED_COVERAGE_ONLY'
            or spec.get('performance_used_to_choose_dates') is not False):
        raise ValueError('Evaluation dates require an evidence-only selection declaration')
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
    if spec['capacity_scenarios'] != [1_000_000, 2_500_000, 5_000_000, 10_000_000]:
        raise ValueError('V2 requires the predeclared 10L, 25L, 50L and 1Cr capital scenarios')
    if not spec['normalization'] or not spec['missing_data_rules'] or not spec['feature_definitions']:
        raise ValueError('Feature definitions and missing-data/normalization rules cannot be empty')
    return spec


def validate_coverage_reports(spec, reports):
    from quant.research.coverage_policy import reliable_interval
    if not reports or set(reports) != {'filings', 'shares'}:
        raise ValueError('Freeze requires certified filing and historical-share coverage reports')
    start, end = spec['evaluation_windows'][0]['from'], spec['evaluation_windows'][-1]['to']
    for name, report in reports.items():
        rows = report.get('periods', [])
        overall, top = ('coverage_pct', 'top_liquidity_coverage_pct') if name == 'filings' else ('verified_share_coverage', 'top100_verified_share_coverage')
        if not rows or any(type(r.get(k)) not in (int, float) or not 0 <= r[k] <= 100
                           for r in rows for k in (overall, top)):
            raise ValueError('Coverage certification requires assessed monthly percentages')
        checked = [dict(r, thresholds_met=r[overall] >= 80 and r[top] >= 90) for r in rows]
        reliable = reliable_interval(checked, minimum_months=spec['coverage_policy']['minimum_consecutive_months'])
        if (not reliable or len([r for r in checked if reliable <= r['as_of'] < start]) < spec['coverage_policy']['minimum_consecutive_months']
                or pd.Period(checked[-1]['as_of'], freq='M') < pd.Period(end, freq='M')
                or (name == 'filings' and report.get('frequency') != 'monthly')):
            raise ValueError('Certified continuous monthly coverage must precede and span OOS dates')
    return reports


def verify_coverage_inputs(record, data_dir):
    """Reject frozen certificates whose immutable input files have changed."""
    base = Path(data_dir).resolve()
    for report in record['coverage_reports'].values():
        paths = dict(report.get('input_sha256', {}))
        provenance = report.get('input_provenance', {})
        paths.update(provenance.get('financial_files', {}))
        for name, expected in paths.items():
            path = (base/name).resolve()
            if not path.is_relative_to(base) or not path.is_file() or digest_file(path) != expected:
                raise ValueError('Frozen coverage source is missing or changed')


def freeze_specification(spec, output, *, coverage_reports=None, governance_review=None, data_interval=None):
    validate_specification(spec)
    validate_coverage_reports(spec, coverage_reports)
    from quant.research.data_interval import require_data_interval
    from quant.governance.review import require_review
    require_data_interval(data_interval or {}, coverage_reports['filings'], coverage_reports['shares'])
    require_review(governance_review, review_type='V2_SPEC_APPROVAL',
                   subject_sha256=specification_subject(spec, coverage_reports, data_interval), decision='APPROVE')
    # One version has one policy in a specification store. Re-evaluation requires
    # the same frozen record; policy edits require a new spec_version.
    import re
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,95}', spec['spec_version']):
        raise ValueError('Invalid specification version')
    output = Path(output)
    append_record(output.parent/'.specification-versions'/f'{spec["spec_version"]}.json',
        dict(specification_sha256=content_hash(spec), source_code_sha256=research_code_hashes()))
    from quant.storage.research_store import git_commit
    body=dict(specification=spec,source_code_sha256=research_code_hashes(), git_commit=git_commit(),
              coverage_reports=coverage_reports,
              data_interval=data_interval, governance_review=governance_review,
              coverage_report_sha256={k:content_hash(v) for k,v in coverage_reports.items()},
              frozen_at=datetime.now(timezone.utc).isoformat())
    append_record(output,dict(**body,sha256=content_hash(body)))


def load_specification(path):
    record=json.loads(Path(path).read_text())
    if record.get('sha256')!=content_hash({k:v for k,v in record.items() if k!='sha256'}):
        raise ValueError('Frozen specification checksum changed')
    if record['source_code_sha256']!=research_code_hashes():
        raise ValueError('Research implementation changed after specification freeze; review a new specification')
    from quant.storage.research_store import git_commit
    if record.get('git_commit') != git_commit():
        raise ValueError('Specification is bound to a different code SHA')
    spec = validate_specification(record['specification'])
    reports = validate_coverage_reports(spec, record.get('coverage_reports'))
    if record.get('coverage_report_sha256') != {k:content_hash(v) for k,v in reports.items()}:
        raise ValueError('Frozen coverage evidence changed')
    from quant.research.data_interval import require_data_interval
    from quant.governance.review import require_review
    require_data_interval(record.get('data_interval', {}), reports['filings'], reports['shares'])
    require_review(record.get('governance_review'), review_type='V2_SPEC_APPROVAL',
        subject_sha256=specification_subject(spec, reports, record['data_interval']), decision='APPROVE')
    return spec


def specification_subject(spec, reports, interval):
    from quant.storage.research_store import git_commit
    return content_hash(dict(specification=spec, git_commit=git_commit(),
        source_code_sha256=research_code_hashes(),
        coverage_report_sha256={k: content_hash(v) for k, v in reports.items()},
        data_interval_sha256=interval['sha256']))
