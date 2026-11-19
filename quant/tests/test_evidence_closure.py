"""Evidence-closure regressions: causal priorities, immutable releases and admission."""
from datetime import date
import json
from types import SimpleNamespace

import pandas as pd
import pytest

from quant.forward.signal_store import content_hash
from quant.storage.research_store import write_json, digest_file
from quant.features.tests.test_fundamental_snapshot import filing


def test_static_official_source_satisfies_dataset_despite_blocked_api():
    from quant.data.source_health import SourceHealth, source_health_gates
    from quant.data.source_requirements import PIPELINE_DATASETS
    observations = [dict(dataset=d, source_id='official-static-'+d, source_class='OFFICIAL_STATIC_ARCHIVE',
        status='READY', provenance_verified=True, verified_session='2026-11-17')
        for d in PIPELINE_DATASETS['historical_research']]
    live = SourceHealth(source_id='nse-api', live_api_ready='UNAVAILABLE', failure_class='HTTP_403_ACCESS_DENIED')
    report = source_health_gates([live], required_session='2026-11-17', dataset_observations=observations)
    assert report['historical_research_ready'] and report['current_eod_ready']
    assert not report['fundamental_acquisition_ready'] and not report['production_publish_ready']
    observations[0]['source_class'] = 'ARCHIVED_CHECKSUMMED_SOURCE'
    assert not source_health_gates([live], required_session='2026-11-17', dataset_observations=observations)['historical_research_ready']
    observations[0]['checksum_verified'] = True
    observations[0]['verified_session'] = '2026-11-16'
    report = source_health_gates([live], required_session='2026-11-17', dataset_observations=observations)
    assert report['historical_research_ready'] and not report['current_eod_ready']


def test_acquisition_classifies_missing_urls_without_claiming_attempts():
    from quant.pipeline.report_fundamental_acquisition import acquisition_report
    rows = pd.DataFrame([filing(filing_id='missing-url', document_sha256=None, source_document=None),
                         filing(filing_id='network', document_sha256=None, source_document='https://official.example/a.xml')])
    report = acquisition_report(rows, {'network':dict(parser_status='NEEDS_REVIEW', review=[dict(reason='HTTP 403')])},
        start='2024-01-01', end='2024-12-31')
    assert report['terminal_status_count'] == 1 and report['attempted_count'] == 1
    assert report['terminal_status_counts'] == {'MISSING_SOURCE_URL':1, 'RETRYABLE_FAILURE':1}
    assert not report['stage1_complete'] and report['unattempted_in_scope'] == 0
    assert report['usable_document_pct'] == 0 and report['unattempted_count'] == 1


def planner_fixture():
    from quant.pipeline.audit_fundamental_coverage import audit_fundamental_coverage
    sessions = pd.bdate_range('2024-08-01', '2024-10-31')
    dates = [pd.Timestamp('2024-08-30'), pd.Timestamp('2024-09-30'), pd.Timestamp('2024-10-31')]
    universe = pd.DataFrame([dict(as_of=d, instrument_id=n, eligible=True, adv60=1_000_000-i, symbol=n.upper())
                            for d in dates for i, n in enumerate(('a','b','c'))])
    filings = pd.DataFrame([filing(filing_id='a-long', document_sha256=None, source_document='https://official.example/a.xml'),
        filing(filing_id='a-overlap', document_sha256=None, period_start='2023-04-01',
               period_end='2024-03-31', period_type='Annual', source_document='https://official.example/a2.xml'),
        filing(filing_id='b-later', instrument_id='b', symbol='B', document_sha256=None,
               exchange_disseminated_at='2024-09-01T16:00:00+05:30', source_document='https://official.example/b.xml'),
        filing(filing_id='c-future', instrument_id='c', symbol='C', document_sha256=None,
               exchange_disseminated_at='2025-01-01T16:00:00+05:30', source_document='https://official.example/c.xml')])
    audit = audit_fundamental_coverage(universe, filings, sessions, start=date(2024,8,1), end=date(2024,10,31))
    return universe, filings, audit


def test_planner_priorities_are_causal_marginal_and_return_independent():
    from quant.pipeline.plan_fundamental_acquisition import plan_acquisition
    universe, filings, audit = planner_fixture()
    result = plan_acquisition(universe, audit, filings)
    assert result['performance_used_to_prioritize'] is False
    selected = {r['filing_id']:r for r in result['candidates']}
    assert result['candidates'][0]['filing_id'] == 'a-long'
    assert selected['a-long']['potential_marginal_name_months'] == 3
    assert 'a-overlap' not in selected
    assert selected['b-later']['repair_months'] == ['2024-09-30', '2024-10-31']
    assert 'c-future' not in selected
    universe['future_return'] = 9999.
    filings['future_return'] = -9999.
    assert plan_acquisition(universe, audit, filings) == result


def test_coverage_deficits_reconcile_and_shares_remain_unassessed():
    universe, filings, audit = planner_fixture()
    first = audit['periods'][0]
    assert first['overall_gap_to_80'] == 80 and first['top100_gap_to_90'] == 90
    assert first['missing_unattempted'] == 1 and first['missing_timing_failure'] == 2
    assert first['missing_share_failure'] is None and first['share_assessment'] == 'UNASSESSED'
    assert len(first['missing_details']) == first['eligible_universe_count']-first['usable_fundamentals_count']


def test_planner_rejects_denominator_substitution():
    from quant.pipeline.plan_fundamental_acquisition import plan_acquisition
    universe, filings, audit = planner_fixture()
    with pytest.raises(ValueError, match='denominators'):
        plan_acquisition(universe[universe.instrument_id.ne('c')], audit, filings)


def test_superseded_documents_cannot_claim_later_coverage_repairs():
    from quant.pipeline.audit_fundamental_coverage import audit_fundamental_coverage
    from quant.pipeline.plan_fundamental_acquisition import plan_acquisition
    universe, filings, _ = planner_fixture()
    filings = filings[filings.filing_id.eq('a-long')]
    revised = filings.copy()
    revised['filing_id'] = 'a-revised'
    revised['revision_at'] = '2024-10-01T12:00:00+05:30'
    filings = pd.concat([filings, revised], ignore_index=True)
    audit = audit_fundamental_coverage(universe, filings, pd.bdate_range('2024-08-01', '2024-10-31'),
        start='2024-08-01', end='2024-10-31')
    plan = plan_acquisition(universe, audit, filings)
    selected = {r['filing_id']:r for r in plan['candidates']}
    assert selected['a-long']['repair_months'] == ['2024-08-30', '2024-09-30']
    assert selected['a-revised']['repair_months'] == ['2024-10-31']


def test_exhaustion_cannot_skip_hashes_review_or_performance_independence():
    from quant.tests.test_evidence_champion_challenger import blocker
    from quant.research.evaluation_window import validate_search_audit
    for changes in ({'evidence_hashes':{}}, {'missing_facts':[]}, {'reviewed_at':None},
                    {'performance_used_to_choose_start':True}):
        with pytest.raises(ValueError):
            validate_search_audit(dict(blocker(), **changes))


def test_spec_cannot_freeze_before_coverage_or_from_averages(tmp_path):
    from quant.tests.test_multifactor_engine import reviewed_spec, synthetic_coverage_reports
    from quant.research.specification import freeze_specification
    spec = reviewed_spec()
    with pytest.raises(ValueError, match='coverage reports'):
        freeze_specification(spec, tmp_path/'no-coverage.json')
    reports = synthetic_coverage_reports(spec)
    reports['filings']['periods'][4]['coverage_pct'] = 79.
    # Make the remaining pre-test history shorter than twelve months.
    reports['filings']['periods'] = reports['filings']['periods'][3:]
    with pytest.raises(ValueError, match='coverage must precede'):
        freeze_specification(spec, tmp_path/'bad-coverage.json', coverage_reports=reports)


def test_incidents_preserve_resolution_history_and_detect_tampering(tmp_path):
    from quant.monitoring.incidents import IncidentLedger
    ledger = IncidentLedger(tmp_path/'incidents')
    with pytest.raises(ValueError, match='uninitialized'):
        ledger.report()
    opened = ledger.open('TRANSITION_ERROR', severity='HIGH', affected_models=['v2'],
        affected_cohorts=[], affected_dates=['2026-11-17'], evidence={'sha256':'a'*64})
    assert ledger.report(model_id='v2')['counts']['transition'] == 1
    assert ledger.report(model_id='v1')['unresolved_incidents'] == 0
    first = ledger.snapshot()['sha256']
    ledger.resolve(opened['incident_id'], resolution='Verified replacement source', reviewer='test-review', evidence=['source'])
    assert ledger.report()['unresolved_incidents'] == 0 and ledger.snapshot()['sha256'] != first
    assert len(list((ledger.root/'events').glob('*.json'))) == 2
    path = ledger.root/'events/00000000.json'
    value = json.loads(path.read_text())
    value['incident']['evidence'] = ['changed']
    write_json(path, value)
    with pytest.raises(ValueError, match='checksum'):
        ledger.report()


def test_live_incident_blocks_champion_before_forward_admission(tmp_path):
    from quant.tests.test_evidence_champion_challenger import validated_registry
    from quant.monitoring.incidents import IncidentLedger
    registry, _ = validated_registry(tmp_path)
    ledger = IncidentLedger(tmp_path/'incidents')
    ledger.open('SOURCE_OUTAGE', severity='CRITICAL', affected_models=['factor-v2-test'],
                affected_cohorts=[], affected_dates=[], evidence=['HTTP 403'])
    with pytest.raises(ValueError, match='zero unresolved'):
        registry.transition('factor-v2-test', 'FORWARD_CHAMPION', reason='synthetic', incident_root=ledger.root)


def test_registry_rejects_a_card_claiming_a_different_historical_interval(tmp_path):
    from quant.tests.test_evidence_champion_challenger import validated_registry
    from quant.models.registry import ModelRegistry
    registry, _ = validated_registry(tmp_path/'original')
    card = registry.card('factor-v2-test')
    card.update(model_id='wrong-interval', test_window={'from':'2025-01-01', 'to':'2026-01-01'})
    other = ModelRegistry(tmp_path/'other')
    other.register(card)
    other.transition('wrong-interval', 'RESEARCH_CANDIDATE', reason='synthetic')
    with pytest.raises(ValueError, match='evaluation interval'):
        other.transition('wrong-interval', 'HISTORICALLY_VALIDATED', reason='synthetic')


def test_release_is_portable_and_detects_changed_or_added_bytes(tmp_path):
    from quant.tests.test_evidence_champion_challenger import validated_registry
    from quant.backtest.artifacts import seal_backtest
    from quant.models.registry import ModelRegistry
    from quant.research.release import build_research_release, verify_research_release
    registry, experiment = validated_registry(tmp_path/'original')
    # A new synthetic candidate binds a complete evidence artifact set.
    (experiment/'completion.json').unlink()
    for name in ('filing-coverage.json', 'share-history-coverage.json', 'window-00/factor-evidence.json',
                 'window-00/factor_v2/metrics.json', 'window-00/factor_v2/risk-evidence.json'):
        write_json(experiment/name, {'scope':'SYNTHETIC_TEST_ONLY'})
    seal_backtest(experiment)
    card = registry.card('factor-v2-test')
    card.update(model_id='complete-test', historical_completion_sha256=digest_file(experiment/'completion.json'))
    new = ModelRegistry(tmp_path/'complete-registry')
    new.register(card)
    new.transition('complete-test', 'RESEARCH_CANDIDATE', reason='synthetic')
    new.transition('complete-test', 'HISTORICALLY_VALIDATED', reason='synthetic')
    output = build_research_release(new.root, 'complete-test', tmp_path/'release')
    assert verify_research_release(output)['status'] == 'VERIFIED'
    moved = tmp_path/'portable'
    output.rename(moved)
    assert verify_research_release(moved)['model_id'] == 'complete-test'
    with pytest.raises(ValueError, match='new and outside'):
        build_research_release(new.root, 'complete-test', moved)
    (moved/'metrics.json').write_text('{}')
    with pytest.raises(ValueError, match='checksum'):
        verify_research_release(moved)


def test_certification_reports_unknown_counts_and_remote_failure(tmp_path, monkeypatch):
    import requests
    from quant.config import Config
    from quant.pipeline import certify_implementation as module
    monkeypatch.setattr(module, 'git_commit', lambda:'a'*40)
    monkeypatch.setattr(module.subprocess, 'run', lambda *a, **k:SimpleNamespace(stdout=''))
    monkeypatch.setattr(module, 'local_checks', lambda:{k:dict(status='PASS') for k in
        ('dependency_check', 'compile_check', 'whitespace_check')})
    def unavailable(*a, **k):
        raise requests.ConnectionError('offline')
    report = module.certify_implementation(Config(data_dir=tmp_path), session=SimpleNamespace(get=unavailable))
    assert report['status'] == 'NOT_CERTIFIED' and report['certified_at'] is None
    assert report['unit_test_count'] is None and report['live_test_status'] == 'UNASSESSED'
    assert report['remote_error'] == 'offline'


def test_v2_distinguishes_absent_insufficient_and_failed_evidence():
    from quant.research.multifactor import v2_decision
    from quant.tests.test_multifactor_engine import reviewed_spec
    criteria = reviewed_spec()['acceptance']
    assert v2_decision([], criteria)['decision'] == 'BLOCKED'
    metrics = dict(observations=600, label_coverage=1., mean_IC=.02, information_ratio=.3,
                   Sharpe=1., max_drawdown=-.1, turnover=2., annualized_excess_return=.03)
    arms = {'matched_v1':dict(metrics=dict(metrics, mean_IC=.01, information_ratio=.1)),
            'factor_v2':dict(metrics=metrics, stress={'1.5':dict(annualized_excess_return=.01)}),
            'risk_budgeted_v2':dict(risk_evidence={'capacity_violations':0})}
    assert v2_decision([arms], criteria)['decision'] == 'GO_FURTHER_V2_RESEARCH'
    arms['factor_v2']['metrics']['mean_IC'] = -.1
    assert v2_decision([arms], criteria)['decision'] == 'NO_GO_V2'
    arms['factor_v2']['metrics']['observations'] = 10
    assert v2_decision([arms], criteria)['decision'] == 'INCONCLUSIVE'


def test_comparison_rejects_matched_dates_with_different_market_bytes(tmp_path, monkeypatch):
    from quant.config import Config
    from quant.pipeline import report_forward_comparison as module
    settings = dict(portfolio={}, costs={}, return_basis='TOTAL_RETURN',
                    security_transition_version='test', lifecycle_scenario='test')
    def make(root, market_hash):
        manifest = dict(files=[dict(path='prices', sha256=market_hash)], input_sha256=market_hash, as_of='2026-11-17')
        digest = content_hash(manifest)
        write_json(root/'sources'/f'{digest}.json', manifest)
        return [dict(as_of='2026-11-17', settings=settings, signals=[dict(source_manifest_hash=digest)],
                     next_session_open='2026-11-18T09:15:00+05:30')]
    roots = dict(v1=tmp_path/'v1', v2=tmp_path/'v2')
    batches = {roots['v1']:make(roots['v1'], 'a'*64), roots['v2']:make(roots['v2'], 'b'*64)}
    monkeypatch.setattr(module, 'read_signals', lambda root:(batches[root], pd.DataFrame()))
    monkeypatch.setattr(module, 'report_forward_cohort', lambda *a, **k:{'scope':'SYNTHETIC_ONLY'})
    with pytest.raises(ValueError, match='identical market'):
        module.report_forward_comparison(Config(data_dir=tmp_path), roots, as_of='2026-11-17', output=tmp_path/'report.json')
    batches[roots['v2']] = make(roots['v2'], 'a'*64)
    assert module.report_forward_comparison(Config(data_dir=tmp_path), roots, as_of='2026-11-17',
                                             output=tmp_path/'report.json')['matched_signal_dates'] == ['2026-11-17']


def test_frozen_coverage_input_changes_block_evaluation(tmp_path):
    from quant.research.specification import verify_coverage_inputs
    path = tmp_path/'filings.parquet'
    path.write_bytes(b'original source')
    record = dict(coverage_reports={'filings':dict(input_provenance=dict(financial_files={path.name:digest_file(path)}))})
    verify_coverage_inputs(record, tmp_path)
    path.write_bytes(b'changed source')
    with pytest.raises(ValueError, match='missing or changed'):
        verify_coverage_inputs(record, tmp_path)
