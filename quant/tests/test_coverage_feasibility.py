"""Feasibility must respect historical identity, revisions and evidence gaps."""
from datetime import date

import pandas as pd
import pytest

from quant.config import Config
from quant.forward.signal_store import content_hash
from quant.pipeline.audit_fundamental_coverage import audit_fundamental_coverage
from quant.pipeline.plan_fundamental_discovery_expansion import plan_discovery_expansion
from quant.pipeline.report_fundamental_coverage_ceiling import coverage_ceiling
from quant.storage.research_store import write_json, digest_file
from quant.tests.test_evidence_closure import planner_fixture


def audit(universe, filings):
    return audit_fundamental_coverage(universe, filings, pd.bdate_range('2024-08-01', '2024-10-31'),
        start='2024-08-01', end='2024-10-31')


def test_ceiling_and_discovery_reconcile_without_future_or_double_repairs():
    universe, filings, coverage = planner_fixture()
    ceiling = coverage_ceiling(universe, coverage, filings)
    assert [r['missing_with_candidate_document'] for r in ceiling['periods']] == [1, 2, 2]
    assert [r['missing_without_candidate_document'] for r in ceiling['periods']] == [2, 1, 1]
    assert all(r['classification'] == 'UNREACHABLE_WITH_CURRENT_DISCOVERY' for r in ceiling['periods'])
    assert ceiling['periods'][0]['theoretical_max_coverage'] == pytest.approx(100/3)
    plan = plan_discovery_expansion(universe, coverage, ceiling)
    assert plan['target_name_months'] == 4 and plan['target_names'] == 2
    assert {r['instrument_id'] for r in plan['targets']} == {'b', 'c'}
    assert not ceiling['coverage_certified'] and not plan['performance_used_to_prioritize']
    universe['future_return'] = 9999
    filings['future_return'] = -9999
    assert coverage_ceiling(universe, coverage, filings) == ceiling
    assert plan_discovery_expansion(universe, coverage, ceiling) == plan


@pytest.mark.parametrize('parsed,classification', [(False, 'REACHABLE'), (True, 'ALREADY_PASSING')])
def test_ceiling_separates_achieved_from_possible(parsed, classification):
    universe, filings, _ = planner_fixture()
    filings['exchange_disseminated_at'] = '2024-08-01T16:00:00+05:30'
    if parsed:
        filings['document_sha256'] = 'a'*64
        filings['parser_status'] = 'PARSED'
    ceiling = coverage_ceiling(universe, audit(universe, filings), filings)
    assert {r['classification'] for r in ceiling['periods']} == {classification}
    assert all(r['theoretical_max_coverage'] == 100 for r in ceiling['periods'])
    assert ceiling['theoretical_reliable_start'] is None  # Three months cannot certify a year.


def test_ceiling_rejects_identity_substitution_and_stale_discovery_audit():
    universe, filings, coverage = planner_fixture()
    ceiling = coverage_ceiling(universe, coverage, filings)
    changed = universe.copy()
    changed.loc[changed.instrument_id.eq('c'), 'instrument_id'] = 'other'
    with pytest.raises(ValueError, match='identities'):
        coverage_ceiling(changed, coverage, filings)
    with pytest.raises(ValueError, match='stale'):
        plan_discovery_expansion(changed, coverage, ceiling)


def test_terminal_unsupported_disclosures_and_ambiguous_revisions_do_not_inflate_ceiling():
    universe, filings, _ = planner_fixture()
    filings = filings[filings.filing_id.eq('a-long')].copy()
    attempts = {'a-long': dict(parser_status='NEEDS_REVIEW', review=[dict(reason='UNSUPPORTED_DOCUMENT')])}
    assert all(r['missing_with_candidate_document'] == 0 for r in
               coverage_ceiling(universe, audit(universe, filings), filings, attempts=attempts)['periods'])
    duplicate = filings.copy()
    duplicate['filing_id'] = 'conflicting-a'
    filings = pd.concat([filings, duplicate], ignore_index=True)
    assert all(r['missing_with_candidate_document'] == 0 for r in
               coverage_ceiling(universe, audit(universe, filings), filings)['periods'])


def test_retryable_failures_need_reviewed_exhaustion_and_frozen_scope():
    from quant.pipeline.report_fundamental_acquisition import acquisition_report
    _, filings, _ = planner_fixture()
    filings = filings[filings.filing_id.eq('a-long')]
    attempt = dict(parser_status='NEEDS_REVIEW', review=[dict(reason='HTTP 403')], attempt_count=3)
    result = acquisition_report(filings, {'a-long': attempt}, start='2024-01-01', end='2024-12-31')
    assert result['terminal_status_count'] == 0 and not result['stage1_complete']
    attempt['retry_exhaustion'] = dict(max_attempts=3, reviewed_by='test reviewer',
        reviewed_at='2024-12-31T20:00:00+05:30', reason='Declared bounded retry budget exhausted')
    result = acquisition_report(filings, {'a-long': attempt}, start='2024-01-01', end='2024-12-31', candidate_set=['a-long'])
    assert result['stage1_complete'] and result['terminal_status_counts'] == {'RETRYABLE_EXHAUSTED': 1}
    assert result['candidate_set_sha256'] == content_hash(['a-long'])
    with pytest.raises(ValueError, match='disappeared'):
        acquisition_report(filings, {}, start='2024-01-01', end='2024-12-31', candidate_set=['missing'])


def test_unreviewed_parser_failure_is_not_permanent_review():
    from quant.pipeline.report_fundamental_acquisition import terminal_status
    assert terminal_status('NEEDS_REVIEW', False, 'https://official.example/a') == 'NEEDS_REVIEW'
    assert terminal_status('NEEDS_REVIEW', False, 'https://official.example/a',
        dict(permanent_review=dict(reviewed_by='test reviewer', reviewed_at='2024-12-31T20:00:00+05:30',
                                   reason='Unsupported fact context retained for review'))) == 'PERMANENT_REVIEW'


def test_changed_input_or_attempt_state_invalidates_acquisition_plan(tmp_path):
    from quant.pipeline.plan_fundamental_acquisition import plan_acquisition, load_plan, acquisition_state_hash
    universe, filings, coverage = planner_fixture()
    plan = plan_acquisition(universe, coverage, filings)
    assert plan['acquisition_state_sha256'] != acquisition_state_hash(filings, {'a-long': {'parser_status': 'PARSED'}})
    source = tmp_path/'source.json'
    source.write_text('original')
    plan['input_sha256'] = {str(source): digest_file(source)}
    plan['sha256'] = content_hash({k: v for k, v in plan.items() if k != 'sha256'})
    path = tmp_path/'plan.json'
    write_json(path, plan)
    assert load_plan(path) == plan
    source.write_text('changed')
    with pytest.raises(ValueError, match='inputs changed'):
        load_plan(path)


def test_bounded_batch_acquires_only_planned_documents_and_rejects_reuse(tmp_path, monkeypatch):
    from contextlib import nullcontext
    from unittest.mock import Mock
    from quant.pipeline import backfill_fundamental_documents as batch
    from quant.pipeline.plan_fundamental_acquisition import plan_acquisition
    from quant.features.tests.test_fundamental_snapshot import filing
    from quant.storage.parquet_store import write_parquet
    universe, _, _ = planner_fixture()
    rows = pd.DataFrame([filing(filing_id=iid, instrument_id=iid, document_sha256=None,
        source_document='https://nsearchives.nseindia.com/'+iid+'.xml', first_seen_at='2024-08-02T16:00:00+05:30',
        source_url='https://www.nseindia.com/api/test', source_sha256='a'*64, metadata_raw_path='raw.json',
        standalone_or_consolidated='Consolidated' if iid == 'a' else 'Standalone') for iid in ('a', 'b')])
    write_parquet(rows, tmp_path/'normalized/financials/metadata.parquet')
    write_parquet(pd.DataFrame(), tmp_path/'normalized/security_history/identities.parquet')
    plan = plan_acquisition(universe, audit(universe, rows), rows)
    assert [r['filing_id'] for r in plan['candidates']] == ['a']
    plan_path = tmp_path/'plan.json'
    write_json(plan_path, plan)
    monkeypatch.setattr(batch, 'NseClient', lambda _: nullcontext(object()))
    monkeypatch.setattr(batch, 'FinancialVersionStore', lambda _: Mock())
    def parsed(client, frame, *args):
        frame['parser_status'], frame['document_sha256'] = 'PARSED', 'b'*64
        return frame, []
    monkeypatch.setattr(batch, 'archive_filings', parsed)
    monkeypatch.setattr('quant.pipeline.report_fundamental_parser_stability.report_parser_stability', lambda *a: None)
    result = batch.backfill_documents(Config(data_dir=tmp_path), date(2024, 1, 1), date(2024, 12, 31),
                                     limit=100, plan_path=plan_path)
    assert result['attempted_this_batch'] == 1
    with pytest.raises(ValueError, match='stale'):
        batch.backfill_documents(Config(data_dir=tmp_path), date(2024, 1, 1), date(2024, 12, 31),
                                 limit=100, plan_path=plan_path)


def share_inputs():
    anchors = pd.DataFrame([dict(instrument_id='a', effective_date='2024-06-30',
        shares_outstanding=100., exchange_disseminated_at='2024-08-01T16:00:00+05:30',
        source_sha256='a'*64, verification_status='VERIFIED')])
    coverage = pd.DataFrame([dict(instrument_id='a', covered_from='2024-06-30', covered_through='2024-10-31',
        known_at='2024-08-01T16:00:00+05:30', source_sha256='b'*64, verification_status='VERIFIED')])
    return anchors, pd.DataFrame(), coverage


def test_paid_up_capital_anchor_uses_dated_face_value_and_retains_provenance():
    from quant.features.share_history import derive_share_anchors, share_history
    from quant.features.tests.test_fundamental_snapshot import filing
    filings = pd.DataFrame([filing(paid_up_capital=1000., face_value=10., document_sha256='a'*64)])
    anchors = derive_share_anchors(filings)
    assert anchors.shares_outstanding.iloc[0] == 100
    _, events, coverage = share_inputs()
    keys = pd.DataFrame([dict(instrument_id='a', signal_timestamp='2024-08-30T15:30:00+05:30')])
    result = share_history(anchors, events, coverage, keys).iloc[0]
    assert result.value_feature_valid and result.shares_outstanding == 100
    assert result.verification_status == 'VERIFIED' and len(result.source) == 2
    assert not share_history(anchors, events, pd.DataFrame(), keys).value_feature_valid.iloc[0]
    filings['face_value'] = 0
    assert derive_share_anchors(filings).empty


@pytest.mark.parametrize('event_type,fields,expected', [
    ('SPLIT', {'share_multiplier': 2.}, 200.), ('BONUS', {'share_multiplier': 1.5}, 150.),
    ('BUYBACK', {'shares_after': 80.}, 80.), ('ISSUANCE', {'shares_after': 120.}, 120.),
    ('MERGER', {'shares_after': 110.}, 110.)])
def test_share_history_replays_verified_capital_actions(event_type, fields, expected):
    from quant.features.share_history import share_history
    anchors, _, coverage = share_inputs()
    events = pd.DataFrame([dict(instrument_id='a', effective_date='2024-08-10',
        announced_at='2024-08-05T16:00:00+05:30', verification_status='VERIFIED',
        source_sha256='c'*64, event_type=event_type, **fields)])
    keys = pd.DataFrame([dict(instrument_id='a', signal_timestamp='2024-08-30T15:30:00+05:30')])
    result = share_history(anchors, events, coverage, keys).iloc[0]
    assert result.shares_outstanding == expected and result.effective_date == '2024-08-10'
    events['verification_status'] = 'NEEDS_REVIEW'
    assert not share_history(anchors, events, coverage, keys).value_feature_valid.iloc[0]


def test_share_ceiling_requires_a_dated_anchor_and_a_complete_event_interval():
    from quant.pipeline.plan_share_evidence import plan_share_evidence
    universe, _, _ = planner_fixture()
    universe = universe[universe.instrument_id.eq('a')]
    anchors, events, coverage = share_inputs()
    anchors['verification_status'] = 'CANDIDATE'
    coverage['verification_status'] = 'CANDIDATE'
    kwargs = dict(start='2024-08-01', end='2024-10-31')
    sessions = pd.bdate_range(kwargs['start'], kwargs['end'])
    result = plan_share_evidence(universe, anchors, events, coverage, sessions, **kwargs)
    assert all(r['current_verified_share_coverage'] == 0 and r['theoretical_max_verified_share_coverage'] == 100 for r in result['periods'])
    absent = plan_share_evidence(universe, anchors, events, pd.DataFrame(), sessions, **kwargs)
    assert all(r['theoretical_max_verified_share_coverage'] == 0 for r in absent['periods'])
    anchors['exchange_disseminated_at'] = '2025-01-01T16:00:00+05:30'
    future = plan_share_evidence(universe, anchors, events, coverage, sessions, **kwargs)
    assert all(r['theoretical_max_verified_share_coverage'] == 0 for r in future['periods'])


def test_stage1_does_not_reuse_a_plan_for_multiple_batches(tmp_path):
    from quant.pipeline.acquire_fundamentals_stage1 import acquire_stage1
    with pytest.raises(ValueError, match='one bounded batch'):
        acquire_stage1(Config(data_dir=tmp_path), date(2024, 1, 1), date(2024, 12, 31), max_batches=2)
    assert not list(tmp_path.rglob('*.json'))


def test_share_evidence_known_later_cannot_fill_an_earlier_signal():
    from quant.features.share_history import share_history
    anchors, events, coverage = share_inputs()
    anchors['known_at'] = '2024-09-01T16:00:00+05:30'
    keys = pd.DataFrame([dict(instrument_id='a', signal_timestamp='2024-08-30T15:30:00+05:30')])
    assert not share_history(anchors, events, coverage, keys).value_feature_valid.iloc[0]


@pytest.mark.parametrize('change', ['sha', 'workflow', 'status', 'redirect', 'url'])
def test_public_ci_page_cannot_certify_a_different_commit_workflow_or_status(change):
    from types import SimpleNamespace
    from quant.pipeline.certify_implementation import verify_public_run_page
    sha = 'a'*40
    url = 'https://github.com/DakshUbhadia/Market_Pulse/actions/runs/123'
    body = (f'<a href="/DakshUbhadia/Market_Pulse/commit/{sha}">commit</a>'
            '<a href="/DakshUbhadia/Market_Pulse/actions/workflows/quant-tests.yml">workflow</a>'
            '<span class="PageHeader-parentLink-label">Quant unit tests</span>'
            '<span>Status</span><span class="h4 color-fg-default">Success</span>')
    good = SimpleNamespace(get=lambda *a, **k: SimpleNamespace(url=url, text=body, raise_for_status=lambda: None))
    assert verify_public_run_page(good, url, sha, timeout=1)[0]['head_sha'] == sha
    response_url = url
    if change == 'sha':
        body = body.replace(sha, 'b'*40)
    if change == 'workflow':
        body = body.replace('quant-tests.yml', 'quant-integration.yml')
    if change == 'status':
        body = body.replace('Success', 'Failure')
    if change == 'redirect':
        response_url = 'https://github.com/login'
    if change == 'url':
        url += '?redirect=untrusted'
    bad = SimpleNamespace(get=lambda *a, **k: SimpleNamespace(url=response_url, text=body, raise_for_status=lambda: None))
    with pytest.raises(ValueError):
        verify_public_run_page(bad, url, sha, timeout=1)
