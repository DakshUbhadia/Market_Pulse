"""Fail-closed phase controls with archived and explicitly synthetic evidence."""
from dataclasses import asdict, replace
from datetime import date
import json

import numpy as np
import pandas as pd
import pytest

from quant.data.source_health import SourceHealth, source_health_gates, classify_failure
from quant.research.evaluation_window import select_evaluation_window, freeze_evaluation_window, load_evaluation_window
from quant.research.coverage_policy import reliable_interval
from quant.models.registry import ModelRegistry
from quant.models.model_card import make_model_card
from quant.forward.signal_store import content_hash
from quant.storage.research_store import write_json, digest_file
from quant.backtest.artifacts import seal_backtest


def archive_source(**kwargs):
    return replace(SourceHealth(source_id='archive', historical_archive_ready='READY', current_eod_ready='READY',
        last_verified_session='2026-11-17', required_for_historical_research=True, required_for_forward_refresh=True), **kwargs)


def test_live_403_does_not_revoke_archived_historical_research():
    report = source_health_gates([archive_source(), SourceHealth(source_id='live', live_api_ready='UNAVAILABLE',
        failure_class='HTTP_403_ACCESS_DENIED')], required_session='2026-11-17')
    assert report['historical_research_ready'] and report['forward_refresh_ready']
    assert not report['production_publish_ready']


def test_missing_latest_eod_blocks_forward_refresh():
    report = source_health_gates([archive_source(last_verified_session='2026-11-16')], required_session='2026-11-17')
    assert report['historical_research_ready'] and not report['forward_refresh_ready']


def test_checksum_failure_revokes_historical_readiness():
    report = source_health_gates([archive_source(failure_class='CHECKSUM_MISMATCH')], required_session='2026-11-17')
    assert not report['historical_research_ready']


def test_live_health_is_reported_separately():
    report = source_health_gates([archive_source(live_api_ready='UNAVAILABLE')], required_session='2026-11-17')
    assert report['live_source_health'] == 'DEGRADED' and report['historical_research_ready']
    assert not source_health_gates([], required_session='2026-11-17')['historical_research_ready']
    report = source_health_gates([archive_source(), SourceHealth(source_id='live', live_api_ready='READY')], required_session='2026-11-17')
    assert report['live_source_health'] == 'READY'


@pytest.mark.parametrize('status,expected', [(403, 'HTTP_403_ACCESS_DENIED'), (429, 'HTTP_429_RATE_LIMIT'),
    (503, 'HTTP_5XX_SOURCE_FAILURE'), (404, 'ARCHIVE_NOT_FOUND'), (None, 'NETWORK_FAILURE')])
def test_source_failure_classes_are_distinct(status, expected):
    assert classify_failure(http_status=status) == expected


def blocker(**kwargs):
    return dict(event_id='TIDEWATER-2016-03-17', mandatory_held_event=True, boundary_date='2016-03-17',
        status='EVIDENCE_EXHAUSTED_UNRESOLVED', sources_checked=['official exchange', 'issuer', 'depository'],
        dates_checked=['2016-03-01/2016-04-30'], documents_checked=['synthetic search audit'],
        search_completed_at='2026-11-18T00:00:00+05:30', reviewed_by='synthetic-test',
        reason_transition_cannot_be_certified='Synthetic missing credit and tradability evidence', **kwargs)


def test_fallback_is_derived_from_last_boundary_and_warmup_and_immutable(tmp_path):
    sessions = pd.bdate_range('2016-01-01', '2017-12-31')
    events = [blocker(), dict(blocker(), event_id='later', boundary_date='2016-04-01')]
    window = select_evaluation_window('2016-01-01', sessions, events, warmup_sessions=252)
    assert window['effective_start'] == str(sessions[sessions > '2016-04-01'][252].date())
    assert window['original_baseline_status'] == 'BLOCKED' and not window['performance_used_to_choose_start']
    path = tmp_path/'window.json'
    freeze_evaluation_window(window, path)
    assert load_evaluation_window(path)['effective_start'] == window['effective_start']
    with pytest.raises(ValueError, match='Immutable'):
        freeze_evaluation_window(dict(window, effective_start='2017-12-29'), path)
    tampered = dict(window, effective_start='2017-12-29')
    write_json(path, dict(tampered, sha256=content_hash(tampered)))
    with pytest.raises(ValueError, match='selection rule'):
        load_evaluation_window(path)


@pytest.mark.parametrize('changes', [{'status':'EVIDENCE_SEARCH_ACTIVE'}, {'sources_checked':[]}, {'reviewed_by':''}])
def test_fallback_rejects_active_or_incomplete_evidence_search(changes):
    with pytest.raises(ValueError, match='exhaust|audit'):
        select_evaluation_window('2016-01-01', pd.bdate_range('2016-01-01', '2017-12-31'),
            [dict(blocker(), **changes)], warmup_sessions=252)


def test_coverage_requires_twelve_months_without_holes_or_later_degradation():
    rows = [dict(as_of=str(d.date()), thresholds_met=True) for d in pd.date_range('2024-01-31', periods=12, freq='ME')]
    assert reliable_interval(rows) == '2024-01-31'
    assert reliable_interval(rows[:-1]) is None
    assert reliable_interval(rows[:5]+rows[6:]) is None
    assert reliable_interval([*rows, dict(as_of='2025-01-31', thresholds_met=False)]) is None


def test_historical_share_denominator_rejects_future_anchor():
    from quant.pipeline.audit_share_history_coverage import audit_share_history_coverage
    dates = pd.bdate_range('2024-01-01', '2024-12-31')
    cutoffs = pd.Series(dates, index=dates).groupby(dates.to_period('M')).last()
    universe = pd.DataFrame([dict(as_of=d, instrument_id='a', eligible=True, adv60=1e8) for d in cutoffs])
    anchors = pd.DataFrame([dict(instrument_id='a', effective_date='2023-12-31', shares_outstanding=100.,
        exchange_disseminated_at='2023-12-31T12:00:00+05:30', verification_status='VERIFIED', source_sha256='a'*64)])
    evidence = pd.DataFrame([dict(instrument_id='a', covered_from='2023-12-31', covered_through='2024-12-31',
        known_at='2023-12-31T12:00:00+05:30', verification_status='VERIFIED', source_sha256='a'*64)])
    report = audit_share_history_coverage(universe, anchors, pd.DataFrame(), evidence, dates,
        start=date(2024, 1, 1), end=date(2024, 12, 31))
    assert report['reliable_window_established'] and all(r['verified_share_coverage'] == 100 for r in report['periods'])
    anchors['exchange_disseminated_at'] = '2025-01-01T12:00:00+05:30'
    report = audit_share_history_coverage(universe, anchors, pd.DataFrame(), evidence, dates,
        start=date(2024, 1, 1), end=date(2024, 12, 31))
    assert not report['reliable_window_established'] and all(r['verified_share_coverage'] == 0 for r in report['periods'])


def test_acquisition_counts_unattempted_documents_and_does_not_retry_taxonomy():
    from quant.pipeline.report_fundamental_acquisition import acquisition_report, classify_attempt
    from quant.features.tests.test_fundamental_snapshot import filing
    rows = pd.DataFrame([filing(filing_id=str(i), document_sha256=None, source_document='https://official.example/filing.xml') for i in range(4)])
    attempts = {'0': dict(parser_status='PARSED', document_sha256='a'*64, review=[]),
        '1': dict(parser_status='NEEDS_REVIEW', review=[dict(reason='HTTP 503 source failure', source_status='LIVE_SOURCE_UNAVAILABLE')]),
        '2': dict(parser_status='NEEDS_REVIEW', review=[dict(reason='UNSUPPORTED_CONTEXT_OR_TAXONOMY')])}
    report = acquisition_report(rows, attempts, start='2024-01-01', end='2024-12-31')
    assert report['candidate_documents'] == 4 and report['attempted'] == 3 and report['completion_pct'] == 75
    assert report['retryable_failures'] == 1 and report['permanent_failures'] == 1 and not report['factor_v2_enabled']
    assert classify_attempt(attempts['2']) == ('UNSUPPORTED_DOCUMENT', False)


def card_values(**kwargs):
    from quant.version import FACTOR_V2_VERSION, FUNDAMENTAL_FEATURE_VERSION
    card = dict(model_id='factor-v2-test', model_version=FACTOR_V2_VERSION, feature_version=FUNDAMENTAL_FEATURE_VERSION,
        spec_hash='a'*64, git_commit='b'*40, data_manifest_hash='c'*64,
        training_window='NONE_DETERMINISTIC', validation_window={'method':'synthetic'},
        test_window={'from':'2024-01-01','to':'2026-01-01'}, coverage_policy={'overall':.8, 'top100':.9},
        cost_model_version='india_delivery_1.1.0', risk_policy_version='portfolio_risk_1.0.0',
        historical_metrics={'scope':'SYNTHETIC_ONLY'}, decision='PENDING', decision_reason='Synthetic test candidate')
    card.update(kwargs)
    return card


def test_registry_code_existence_cannot_promote_and_card_tampering_is_detected(tmp_path):
    registry = ModelRegistry(tmp_path)
    registry.register(card_values())
    assert not any(r['state'] == 'FORWARD_CHAMPION' for r in registry.snapshot().values())
    registry.transition('factor-v2-test', 'RESEARCH_CANDIDATE', reason='synthetic research')
    with pytest.raises(ValueError, match='PASS'):
        registry.transition('factor-v2-test', 'HISTORICALLY_VALIDATED', reason='code exists')
    with pytest.raises(ValueError, match='Forbidden'):
        registry.transition('factor-v2-test', 'FORWARD_CHAMPION', reason='single metric')
    path = tmp_path/'cards/factor-v2-test.json'
    card = json.loads(path.read_text())
    card['decision'] = 'PASS'
    write_json(path, card)
    with pytest.raises(ValueError, match='checksum'):
        registry.snapshot()


def validated_registry(tmp_path):
    experiment = tmp_path/'experiment'
    values = card_values()
    spec = {k: values[k] for k in ('model_version', 'feature_version', 'cost_model_version', 'risk_policy_version', 'coverage_policy')}
    manifest = {'files':[]}
    write_json(experiment/'config.json', dict(specification=spec, manifest=manifest, git_commit='b'*40))
    write_json(experiment/'v2-decision.json', dict(decision='GO_FURTHER_V2_RESEARCH'))
    seal_backtest(experiment)
    registry = ModelRegistry(tmp_path/'registry')
    registry.register(card_values(decision='PASS', historical_experiment=str(experiment),
        historical_completion_sha256=digest_file(experiment/'completion.json'),
        spec_hash=content_hash(spec), data_manifest_hash=content_hash(manifest)))
    registry.transition('factor-v2-test', 'RESEARCH_CANDIDATE', reason='synthetic research')
    registry.transition('factor-v2-test', 'HISTORICALLY_VALIDATED', reason='synthetic evidence')
    registry.transition('factor-v2-test', 'FORWARD_CHALLENGER', reason='synthetic forward admission')
    return registry, experiment


def test_registry_requires_sealed_independent_evidence_and_manual_champion_record(tmp_path):
    registry, experiment = validated_registry(tmp_path)
    assert registry.require_forward_candidate('factor-v2-test')['decision'] == 'PASS'
    with pytest.raises(ValueError, match='manual'):
        registry.transition('factor-v2-test', 'FORWARD_CHAMPION', reason='synthetic single metric')
    write_json(experiment/'v2-decision.json', {'decision':'NO_GO_INVESTIGATE'})
    with pytest.raises(ValueError, match='checksum'):
        registry.require_forward_candidate('factor-v2-test')


def test_registry_journal_cannot_rewrite_history_or_delete_middle_events(tmp_path):
    registry, _ = validated_registry(tmp_path)
    (registry.root/'events/00000001.json').unlink()
    with pytest.raises(ValueError, match='sequence'):
        registry.snapshot()


def test_registered_v2_freezes_seven_contributions_and_replays_same_accounting(tmp_path):
    from quant.forward.tests.test_forward import fixture, freeze
    from quant.forward.signal_store import read_signals
    from quant.forward.shadow_portfolio import update_shadow
    from quant.backtest.portfolio import PortfolioConfig
    from quant.backtest.tests.test_simulation import zero_cost
    from quant.models.factor_v2 import BLOCKS
    prices, _, sessions, scores = fixture()
    card = make_model_card(card_values())
    scores['model_version'], scores['feature_version'] = card['model_version'], card['feature_version']
    for block in BLOCKS:
        scores[block+'_score'] = 0.
    settings = dict(model_card_sha256=card['sha256'], portfolio=asdict(PortfolioConfig(holdings=1, max_weight=1)),
        costs=asdict(zero_cost()), lifecycle_scenario='MANDATORY_ECONOMIC_EVENTS_ONLY')
    freeze(tmp_path, scores, model_card=card, settings=settings)
    _, signals = read_signals(tmp_path)
    assert set(signals.factor_contributions.iloc[0]) == set(BLOCKS)
    path = update_shadow(tmp_path, prices, sessions, as_of='2024-11-04', portfolio=PortfolioConfig(holdings=1,max_weight=1),
        cost_model=zero_cost(), corporate_actions=pd.DataFrame(), lifecycle_events=None,
        lifecycle_scenario='MANDATORY_ECONOMIC_EVENTS_ONLY', model_card=card)
    assert json.loads(path.read_text())['equity']['nav'] == pytest.approx(1_000_000)


def test_monitoring_detects_shift_freshness_and_unmatured_ic_without_retraining():
    from quant.monitoring.feature_drift import feature_drift
    from quant.monitoring.factor_ic import factor_ic_drift
    from quant.monitoring.coverage import coverage_health
    from quant.monitoring.data_freshness import data_freshness
    old = pd.DataFrame({'x':np.arange(100, dtype=float)})
    report = feature_drift(old, old+1000, features=['x'])
    assert report['status'] == 'ALERT' and not report['automatic_retraining']
    assert feature_drift(old, old, features=['x'])['status'] == 'PASS'
    assert feature_drift(old, pd.DataFrame(), features=['x'])['status'] == 'UNASSESSED'
    ic = pd.DataFrame(dict(block=['value']*12, IC=[.1]*12, exit_date=['2025-01-01']*12))
    assert factor_ic_drift(ic, ic, as_of='2024-12-31')['factors'][0]['status'] == 'UNASSESSED'
    assert coverage_health(.79, .95)['status'] == 'ALERT'
    assert coverage_health(.9, .95, parser_attempts=10, parser_failures=3)['status'] == 'ALERT'
    assert data_freshness([asdict(archive_source())], required_session='2026-11-18')['status'] == 'ALERT'


def test_earlier_acquisition_cannot_bypass_explicit_stage_decision(tmp_path):
    from quant.config import Config
    from quant.pipeline.backfill_fundamentals import backfill_fundamentals
    with pytest.raises(ValueError, match='explicit decision'):
        backfill_fundamentals(Config(data_dir=tmp_path), date(2020,1,1), date(2026,11,17))
    assert not list(tmp_path.rglob('*.json'))


def test_same_spec_version_cannot_change_thresholds_after_freeze(tmp_path):
    from quant.tests.test_multifactor_engine import reviewed_spec
    from quant.research.specification import freeze_specification
    spec = reviewed_spec()
    freeze_specification(spec, tmp_path/'first.json')
    spec['acceptance']['min_mean_ic_improvement'] = 0.
    with pytest.raises(ValueError, match='Immutable'):
        freeze_specification(spec, tmp_path/'second.json')
    assert not (tmp_path/'second.json').exists()


def test_share_archive_checksum_mismatch_revokes_verified_flag(tmp_path):
    from quant.pipeline.audit_share_history_coverage import verify_share_archives
    path = tmp_path/'anchor.pdf'
    path.write_bytes(b'changed source')
    anchors = pd.DataFrame([dict(raw_path=str(path), source_sha256='a'*64, verification_status='VERIFIED')])
    assert verify_share_archives(anchors, tmp_path).verification_status.iloc[0] == 'NEEDS_REVIEW'


def test_exact_sha_ci_ignores_live_failure_but_blocks_dirty_tree(tmp_path, monkeypatch):
    from quant.config import Config
    from quant.pipeline import certify_implementation as module
    from types import SimpleNamespace
    commit = 'a'*40
    dirty = ['']
    monkeypatch.setattr(module, 'git_commit', lambda: commit)
    monkeypatch.setattr(module.subprocess, 'run', lambda *a, **k: SimpleNamespace(stdout=dirty[0]))
    runs = [dict(id=1, name='Quant unit tests', head_sha=commit, status='completed', conclusion='success', created_at='2026-11-18'),
            dict(id=2, name='Quant live source smoke tests', head_sha=commit, status='completed', conclusion='failure')]
    response = SimpleNamespace(raise_for_status=lambda: None, json=lambda: {'workflow_runs':runs})
    client = SimpleNamespace(get=lambda *a, **k: response)
    assert module.certify_implementation(Config(data_dir=tmp_path), session=client)['status'] == 'CERTIFIED'
    dirty[0] = ' M quant/models/factor_v2.py'
    assert module.certify_implementation(Config(data_dir=tmp_path), session=client)['status'] == 'NOT_CERTIFIED'


def test_value_block_cannot_use_finite_values_with_unverified_shares():
    from quant.features.matrix import SCORE_FEATURES
    from quant.models.factor_v2 import same_universe_scores
    from quant.version import FEATURE_VERSION
    prices = pd.DataFrame(dict(as_of=pd.Timestamp('2024-08-01'), instrument_id=list('abcd'),
        eligible=True, feature_valid=True, feature_version=FEATURE_VERSION))
    for name in SCORE_FEATURES:
        prices[name] = np.arange(4)+1.
        prices['z_'+name] = np.arange(4)-1.5
    fundamentals = prices[['as_of','instrument_id']].assign(entity_type='IND_AS_INDUSTRIAL', value_feature_valid=False)
    for name in ('roe','cfo_pat','debt_equity','revenue_yoy','pat_yoy','earnings_yield','book_yield','fcf_yield'):
        fundamentals[name] = np.arange(4)+1.
    assert same_universe_scores(prices, fundamentals, min_group_size=2)['factor_v2'].empty
