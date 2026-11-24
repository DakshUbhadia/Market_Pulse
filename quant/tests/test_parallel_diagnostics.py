"""Exercise actual accounting/packaging with explicitly synthetic diagnostic inputs."""
import json

import numpy as np
import pandas as pd
import pytest

from quant.config import Config, REPO_ROOT
from quant.storage.research_store import write_json
from quant.tests.research_fixtures import market_fixture


def controlled_v2_inputs():
    from quant.features.matrix import SCORE_FEATURES
    from quant.features.normalize import normalize_cross_section
    from quant.version import FEATURE_VERSION
    prices, benchmark, sessions = market_fixture(stocks=20, days=285, start='2024-01-01')
    features = prices[['trade_date', 'instrument_id', 'symbol']].rename(columns={'trade_date': 'as_of'}).copy()
    features = features.assign(eligible=True, feature_valid=True, feature_version=FEATURE_VERSION,
                               adv60=100_000_000., vol_63=.2)
    ordinal = features.instrument_id.str[-3:].astype(float)
    for i, name in enumerate(SCORE_FEATURES):
        features[name] = ordinal+i+1.
    features['vol_63'] = .15+ordinal/1000
    # Cross-sectional inputs only need the evaluation window. Covariance still
    # uses the full observed price history, so its warmup is exercised unchanged.
    features = features[features.as_of.ge(sessions[265])].copy().reset_index(drop=True)
    ordinal = features.instrument_id.str[-3:].astype(float)
    features = normalize_cross_section(features, SCORE_FEATURES)
    fundamentals = features[['as_of', 'instrument_id']].assign(entity_type='IND_AS_INDUSTRIAL', value_feature_valid=True)
    for field in ('roe', 'cfo_pat', 'debt_equity', 'revenue_yoy', 'pat_yoy', 'earnings_yield', 'book_yield', 'fcf_yield'):
        fundamentals[field] = ordinal+1.
    labels = features[['as_of', 'instrument_id']].assign(label_available=True, exit_date=features.as_of,
        excess_return_63=ordinal/100, stock_return_63=ordinal/100)
    spec = json.loads((REPO_ROOT/'quant/specs/factor_v2_1.0.0.json').read_text())
    spec['evaluation_windows'] = [dict(**{'from': str(sessions[265].date()), 'to': str(sessions[-1].date())})]
    return dict(prices=prices, benchmark=benchmark, sessions=sessions, price_features=features,
        fundamental_features=fundamentals, labels=labels, draft_spec=spec,
        input_scope='SYNTHETIC_CONTROLLED_INPUTS')


def test_v2_matrix_cannot_hide_missing_value_or_freeze_a_draft():
    from quant.pipeline.prepare_v2_matrix import prepare_v2_matrix
    inputs = controlled_v2_inputs()
    arms, report = prepare_v2_matrix(inputs['price_features'], inputs['fundamental_features'])
    assert report['status'] == 'COMPLETE_RESEARCH_INPUTS'
    assert not report['frozen'] and not report['full_v2_enabled']
    inputs['fundamental_features']['value_feature_valid'] = 1
    _, report = prepare_v2_matrix(inputs['price_features'], inputs['fundamental_features'])
    assert report['status'] == 'INCOMPLETE'
    inputs['fundamental_features']['value_feature_valid'] = False
    arms, report = prepare_v2_matrix(inputs['price_features'], inputs['fundamental_features'])
    assert report['status'] == 'INCOMPLETE' and arms['factor_v2'].empty
    assert all(row['verified_value_missing'] == 20 for row in report['periods'])


def test_four_arm_diagnostic_completes_without_historical_decision(tmp_path, monkeypatch):
    from quant.pipeline import run_v2_diagnostics as runner
    from quant.backtest.artifacts import verify_diagnostic_completion
    from quant.research.release import build_diagnostic_release, verify_diagnostic_release
    monkeypatch.setattr(runner, 'require_certified_implementation', lambda *a: dict(scope='SYNTHETIC_TEST_ONLY'))
    folder = runner.run_v2_diagnostics(Config(data_dir=tmp_path), **controlled_v2_inputs())
    completion = verify_diagnostic_completion(folder)
    assert completion['seal_eligible'] is False and completion['governance_status'] == 'PENDING'
    metrics = json.loads((folder/'metrics.json').read_text())['window-00']
    assert len(metrics) == 4
    assert not list(folder.rglob('v2-decision.json')) and not list(folder.rglob('completion.json'))
    assert len(json.loads((folder/'window-00/capacity-scenarios.json').read_text())) == 4
    release = build_diagnostic_release(folder, tmp_path/'release')
    assert verify_diagnostic_release(release)['historical_validation'] is False


@pytest.mark.parametrize('total_return', [False, True])
def test_pending_review_allows_diagnostic_run(tmp_path, monkeypatch, total_return):
    from quant.pipeline import run_backtest as runner
    from quant.backtest.artifacts import verify_diagnostic_completion
    from quant.research.evaluation_window import load_evaluation_window
    from quant.storage.research_store import digest_file
    prices, benchmark, sessions = market_fixture(stocks=3, days=300, start='2023-01-02')
    indices = pd.concat([benchmark.assign(index_name=name) for name in ('NIFTY 50', 'NIFTY 500')])
    actions = pd.DataFrame(columns=['event_id', 'action_type', 'ex_date', 'instrument_id', 'cash_amount', 'parse_status'])
    tri = indices.assign(index_name=indices.index_name+' TRI')
    # Any attempt to compute performance on a fallback diagnostic is a regression.
    def performance_forbidden(*args, **kwargs):
        pytest.fail('Fallback diagnostics must stop before performance measurement')
    monkeypatch.setattr(runner, 'performance_metrics', performance_forbidden)
    monkeypatch.setattr(runner, 'forward_labels', performance_forbidden)
    monkeypatch.setattr(runner, 'require_research_ready', lambda *a: dict(status='SYNTHETIC_TEST_ONLY'))
    monkeypatch.setattr(runner, 'require_certified_implementation', lambda *a: dict(scope='SYNTHETIC_TEST_ONLY'))
    monkeypatch.setattr(runner, 'input_manifest', lambda *a: dict(files=[], input_sha256='synthetic'))
    monkeypatch.setattr(runner, 'load_research_data', lambda *a: (prices, benchmark, sessions, None, indices))
    monkeypatch.setattr(runner, 'query_dataset', lambda root, name, **kw: actions if name == 'corporate_actions' else tri)
    declaration = load_evaluation_window(REPO_ROOT/'quant/artifacts/historical-forward-validation/reports/v1-evaluation-declaration.json', require_admission=False)
    declaration['selection_calendar'] = [str(d.date()) for d in sessions]
    declaration['effective_start'] = '2024-01-02'
    # A short, synthetic declaration boundary keeps CI independent of local
    # source bytes and Windows long-path support. Real declaration validation
    # and evidence-only selection are covered by governance contract tests.
    for event in declaration['blocking_events']:
        destination = tmp_path/'synthetic-evidence.txt'
        destination.write_text('SYNTHETIC_TEST_ONLY')
        event['evidence_hashes'] = {destination.name: digest_file(destination)}
    from quant.forward.signal_store import content_hash
    declaration['sha256'] = content_hash({k: v for k, v in declaration.items() if k != 'sha256'})
    # The immutable declaration's audit has independent checksums. Use the real
    # parsed declaration as the test boundary rather than fabricating admission.
    monkeypatch.setattr('quant.research.evaluation_window.load_evaluation_window', lambda *a, **kw: declaration)
    window = tmp_path/'prepared-window.json'
    write_json(window, declaration)
    path, evidence = runner.run_research(Config(data_dir=tmp_path), pd.Timestamp(declaration['requested_start']).date(),
        sessions[-1].date(), estimate_historical_costs=True, full_robustness=True,
        total_return=total_return, research_authority='DIAGNOSTIC_ONLY', evaluation_window=window)
    assert evidence['status'] == 'DIAGNOSTIC_ONLY'
    assert verify_diagnostic_completion(path)['seal_eligible'] is False
    assert not list(path.rglob('completion.json')) and not (path/'v1-decision.json').exists()
    assert evidence['output_scope'] == 'STRUCTURAL_ONLY'
    assert {f.name for f in path.iterdir()} == {
        'diagnostic-authority.json', 'input-manifest.json', 'structural-summary.json', 'diagnostic-completion.json'}
    assert not list((tmp_path/'research').rglob('prepared-scores.parquet'))


def test_risk_caps_bind_individually_and_turnover_penalty_preserves_holdings():
    from quant.portfolio.constraints import RiskPolicy
    from quant.portfolio.risk_budget import allocate_risk
    names = pd.Index(list('abcd'))
    sigma = pd.DataFrame(np.diag([.01, .02, .03, .04]), index=names, columns=names)
    adv = pd.Series(1e12, index=names)
    groups = pd.Series(list('xxyz'), index=names)
    old = pd.Series(0., index=names)
    weights, report = allocate_risk(sigma, old, adv, groups, nav=1e6,
        policy=RiskPolicy(max_weight=.15, max_cluster_weight=1, target_volatility=1))
    assert np.allclose(weights, .15, atol=1e-7) and report['cash_weight'] == pytest.approx(.4, abs=1e-7)
    weights, report = allocate_risk(sigma, old, adv, pd.Series('x', index=names), nav=1e6,
        policy=RiskPolicy(max_weight=1, max_cluster_weight=.3, target_volatility=1))
    assert weights.sum() == pytest.approx(.3, abs=1e-7)
    weights, report = allocate_risk(sigma, old, adv, groups, nav=1e6,
        policy=RiskPolicy(max_weight=1, max_cluster_weight=1, target_volatility=.02))
    assert report['annualized_volatility'] == pytest.approx(.02, abs=1e-6)
    previous = pd.Series([.1, .2, .3, .4], index=names)
    _, cheap = allocate_risk(sigma, previous, adv, groups, nav=1e6,
        policy=RiskPolicy(max_weight=1, max_cluster_weight=1, target_volatility=1, turnover_penalty=0))
    _, costly = allocate_risk(sigma, previous, adv, groups, nav=1e6,
        policy=RiskPolicy(max_weight=1, max_cluster_weight=1, target_volatility=1, turnover_penalty=1))
    assert costly['turnover'] < cheap['turnover']/10


def test_test_only_forward_matures_and_monitoring_remains_nonpromotable(tmp_path):
    from pathlib import Path
    from quant.forward.tests.test_forward import fixture
    from quant.backtest.tests.test_simulation import zero_cost
    from quant.backtest.portfolio import PortfolioConfig
    from quant.pipeline.run_test_forward import run_test_forward
    from quant.forward.shadow_portfolio import update_shadow
    from quant.forward.outcome_tracker import track_outcomes
    from quant.forward.metrics import forward_metrics
    from quant.pipeline.report_research_monitoring import research_monitoring
    from quant.monitoring.incidents import IncidentLedger
    prices, benchmark, sessions, scores = fixture()
    costs, portfolio = zero_cost(), PortfolioConfig(holdings=1, max_weight=1)
    execution = dict(corporate_actions=None, lifecycle_events=None,
                     lifecycle_scenario='MANDATORY_ECONOMIC_EVENTS_ONLY')
    report = run_test_forward(Config(data_dir=tmp_path), cohort='controlled', prices=prices,
        benchmark=benchmark, tri=benchmark, sessions=sessions, scores=scores, as_of='2024-10-31',
        generated_at='2024-10-31T19:00:00+05:30', next_open='2024-11-01T09:15:00+05:30',
        source_manifest=dict(scope='SYNTHETIC_TEST_ONLY'), diagnostic_subject_sha256='a'*64,
        costs=costs, portfolio=portfolio, **execution)
    root, end = Path(report['root']), str(sessions[-1].date())
    assert report['cohort_type'] == 'TEST_ONLY' and not report['real_forward_evidence']
    from quant.forward.signal_store import read_signals, freeze_signals
    from quant.backtest.engine import monthly_signal_dates
    batch = read_signals(root)[0][0]
    for day in sorted(monthly_signal_dates(sessions)):
        if pd.Timestamp('2024-10-31') < day < sessions[-1]:
            next_day = sessions[sessions.get_loc(day)+1]
            freeze_signals(root, scores.assign(as_of=day), as_of=str(day.date()), data_as_of=str(day.date()),
                generated_at=f'{day.date()}T19:00:00+05:30', next_open=f'{next_day.date()}T09:15:00+05:30',
                git_commit=batch['signals'][0]['git_commit'], source_manifest_hash=batch['signals'][0]['source_manifest_hash'],
                settings=batch['settings'], cohort_type='TEST_ONLY')
    update_shadow(root, prices, sessions, as_of=end, portfolio=portfolio, cost_model=costs, **execution)
    matured = track_outcomes(root, prices, benchmark, benchmark, sessions, as_of=end, cost_model=costs, **execution)
    assert matured['written'] >= 2 and not matured['blocked']
    assert forward_metrics(root)['cohort_type'] == 'TEST_ONLY'
    rows = [json.loads(p.read_text()) for p in (root/'shadow').glob('*.json')]
    curve = pd.DataFrame([dict(trade_date=row['as_of'], **row['equity']) for row in rows]).sort_values('trade_date')
    reference = pd.DataFrame(dict(as_of=pd.Timestamp('2024-09-01'), feature=np.arange(30)))
    current = pd.DataFrame(dict(as_of=pd.Timestamp(end), feature=np.arange(30)+100))
    ref_ic = pd.DataFrame(dict(block='momentum', IC=.1, exit_date=[end]*12))
    current_ic = ref_ic.assign(IC=-.1)
    incidents = tmp_path/'incidents'
    ledger = IncidentLedger(incidents)
    ledger.initialize()
    ledger.open('PARSER_REGRESSION', severity='HIGH', affected_models=[],
        affected_cohorts=[str(root.resolve())], affected_dates=[end], evidence={'scope': 'SYNTHETIC_TEST_ONLY'})
    monitoring = research_monitoring(root=root, as_of=end, reference=reference, current=current,
        features=['feature'], reference_ic=ref_ic, current_ic=current_ic, curve=curve,
        source_health={'sources': [dict(source_id='test', required_for_forward_refresh=True,
            current_eod_ready='STALE', last_verified_session='2024-10-31')]},
        coverage=dict(overall=.7, top100=.8, parser_attempts=10, parser_failures=5),
        cluster_weights={'x': 1.}, incident_root=incidents)
    assert monitoring['status'] == 'REVIEW_REQUIRED'
    assert monitoring['cohort_type'] == 'TEST_ONLY' and not monitoring['promotion_eligible']
    assert monitoring['unresolved_incidents'] == 1
    assert monitoring['panels']['feature_drift']['status'] == 'ALERT'
    assert monitoring['panels']['factor_ic']['factors'][0]['status'] == 'ALERT'
    assert monitoring['panels']['coverage']['status'] == 'ALERT'
    assert monitoring['panels']['freshness']['status'] == 'ALERT'
