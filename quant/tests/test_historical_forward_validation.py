"""Reject automated admission, stale interval evidence and partial capital facts."""
import json

import pandas as pd
import pytest

from quant.forward.signal_store import content_hash
from quant.governance.review import require_review, seal_review
from quant.research.data_interval import certify_data_interval, require_data_interval
from quant.tests.governance_fixtures import human_review


@pytest.mark.parametrize('change', [dict(reviewer_kind='AUTOMATED'), dict(independent_review=False),
    dict(reviewer_name=''), dict(reviewer_role=''), dict(reviewed_at='2099-01-01T00:00:00Z'),
    dict(reviewed_at='2024-01-01'), dict(performance_information_used=True), dict(decision='ADMIT'),
    dict(subject_sha256='b'*64)])
def test_human_governance_rejects_wrong_identity_scope_time_and_performance(change, tmp_path):
    record = human_review('V2_SPEC_APPROVAL', 'a'*64, 'APPROVE')
    record.update(change)
    record['sha256'] = content_hash({k: v for k, v in record.items() if k != 'sha256'})
    with pytest.raises(ValueError):
        require_review(record, review_type='V2_SPEC_APPROVAL', subject_sha256='a'*64, decision='APPROVE')


def test_governance_record_is_immutable_and_checksum_verified(tmp_path):
    record = human_review('PRODUCTION_PUBLISHING', 'a'*64, 'APPROVE')
    path = tmp_path/'review.json'
    seal_review(record, path)
    require_review(json.loads(path.read_text()), review_type='PRODUCTION_PUBLISHING', subject_sha256='a'*64, decision='APPROVE')
    with pytest.raises(ValueError, match='Immutable'):
        seal_review(dict(record, reason='Changed decision rationale'), path)
    record['reason'] = 'Changed'
    with pytest.raises(ValueError, match='checksum'):
        require_review(record, review_type='PRODUCTION_PUBLISHING', subject_sha256='a'*64, decision='APPROVE')


def test_fallback_needs_both_human_exhaustion_and_window_admission(tmp_path):
    from quant.tests.test_evidence_champion_challenger import blocker
    from quant.research.evaluation_window import select_evaluation_window, window_subject, window_subject_id, freeze_evaluation_window, load_evaluation_window
    event = blocker()
    window = select_evaluation_window('2016-01-01', pd.bdate_range('2016-01-01', '2017-12-31'), [event], warmup_sessions=252)
    digest = content_hash(event)
    review = human_review('TRANSITION_EXHAUSTION', digest, 'CONFIRM_EVIDENCE_EXHAUSTED_UNRESOLVED',
        transition_id=event['event_id'], automated_review_sha256=digest,
        sources_reviewed=['Synthetic sources'], facts_proven=['Synthetic proposal'],
        facts_unproven=['Synthetic actual credit date'], search_routes_attempted=['Synthetic exchange route'])
    governance = dict(transition_reviews={event['event_id']: review},
        window_review=human_review('EVALUATION_WINDOW_ADMISSION', window_subject(window), 'ADMIT', subject_id=window_subject_id(window)))
    path = tmp_path/'admitted.json'
    freeze_evaluation_window(window, path, governance=governance)
    assert load_evaluation_window(path)['effective_start'] == window['effective_start']
    for field in ('transition_reviews', 'window_review'):
        bad = dict(governance)
        bad.pop(field)
        with pytest.raises(ValueError):
            freeze_evaluation_window(window, tmp_path/(field+'.json'), governance=bad)
    changed = dict(window, effective_start='2017-12-01')
    with pytest.raises(ValueError):
        freeze_evaluation_window(changed, tmp_path/'changed.json', governance=governance)


def interval_reports():
    dates = pd.date_range('2024-01-31', periods=12, freq='ME')
    return (dict(frequency='monthly', periods=[dict(as_of=str(d.date()), coverage_pct=85., top_liquidity_coverage_pct=95.) for d in dates]),
            dict(periods=[dict(as_of=str(d.date()), verified_share_coverage=85., top100_verified_share_coverage=95.) for d in dates]))


def test_shared_interval_is_bound_to_both_reports_and_same_cutoffs():
    f, s = interval_reports()
    record = certify_data_interval(f, s)
    assert record['certified'] and len(record['monthly_cutoffs']) == 12
    require_data_interval(record, f, s)
    s['periods'][0]['verified_share_coverage'] = 79
    assert not certify_data_interval(f, s)['certified']
    with pytest.raises(ValueError, match='shared'):
        require_data_interval(record, f, s)


@pytest.mark.parametrize('change', ['gap', 'cutoff', 'degradation', 'empty', 'duplicate', 'nan'])
def test_shared_interval_never_uses_averages_or_overlaps_to_hide_failures(change):
    f, s = interval_reports()
    if change == 'gap':
        s['periods'].pop(4)
    if change == 'cutoff':
        s['periods'][3]['as_of'] = '2024-04-29'
    if change == 'degradation':
        s['periods'][-1]['top100_verified_share_coverage'] = 89
    if change == 'empty':
        s['periods'] = []
    if change == 'duplicate':
        s['periods'].append(s['periods'][-1])
    if change == 'nan':
        s['periods'][0]['verified_share_coverage'] = float('nan')
    if change in ('duplicate', 'nan'):
        with pytest.raises(ValueError):
            certify_data_interval(f, s)
    else:
        assert not certify_data_interval(f, s)['certified']


def test_legacy_verified_events_and_unknown_interval_inventory_cannot_modify_shares():
    from quant.tests.test_historical_certification import chain_inputs
    from quant.tests.governance_fixtures import complete_interval
    from quant.data.capital_events import reconcile_share_chain
    a, e, c = chain_inputs()
    cutoff = '2024-08-30T15:30:00+05:30'
    assert reconcile_share_chain(a, e, c, 'a', cutoff)['value_feature_valid']
    e['verification_status'] = 'VERIFIED'
    c = complete_interval(a, e, c)
    assert not reconcile_share_chain(a, e, c, 'a', cutoff)['value_feature_valid']
    e['verification_status'] = 'VERIFIED_COMPLETE'
    c = complete_interval(a, e, c)
    for key, value in [('unresolved_event_count', 1), ('event_inventory_hash', 'f'*64),
                       ('source_coverage', {}), ('reconciled_end_anchor', 'f'*64)]:
        changed = c.copy()
        changed.at[0, key] = value
        assert not reconcile_share_chain(a, e, changed, 'a', cutoff)['value_feature_valid']


def verified_event(tmp_path):
    from quant.storage.research_store import digest_file
    path = tmp_path/'official.json'
    path.write_text('Synthetic official capital event source')
    row = dict(instrument_id='a', security_lineage_id='line-a', event_type='BONUS',
        known_at='2024-04-12T16:00:00+05:30',
        announced_at='2024-04-01T16:00:00+05:30', record_date='2024-04-10', effective_date='2024-04-11',
        credit_date='2024-04-11', listing_date='2024-04-12', share_multiplier=2.,
        verification_status='CANDIDATE', raw_path=path.name, source_sha256=digest_file(path))
    row['event_evidence'] = {k:dict(raw_path=path.name, source_sha256=digest_file(path),
        source_url='https://nsearchives.nseindia.com/evidence', source_type='NSE_OFFICIAL', source_exchange='NSE',
        review_status='VERIFIED', reviewed_by='SYNTHETIC TEST ONLY', value=str(row[k])) for k in
        ('instrument_id', 'event_type', 'security_lineage_id', 'announced_at', 'known_at', 'record_date', 'effective_date', 'credit_date', 'listing_date', 'share_multiplier')}
    return row


def test_capital_verifier_requires_reviewed_terms_dates_lineage_and_source_bytes(tmp_path):
    from quant.pipeline.verify_capital_events import verify_capital_events
    row = verified_event(tmp_path)
    assert verify_capital_events(pd.DataFrame([row]), tmp_path).verification_status.iloc[0] == 'VERIFIED_COMPLETE'
    for key in row['event_evidence']:
        bad = dict(row, event_evidence={k: v for k, v in row['event_evidence'].items() if k != key})
        assert verify_capital_events(pd.DataFrame([bad]), tmp_path).verification_status.iloc[0] != 'VERIFIED_COMPLETE'
    (tmp_path/'official.json').write_text('Changed source')
    assert verify_capital_events(pd.DataFrame([row]), tmp_path).verification_status.iloc[0] != 'VERIFIED_COMPLETE'


def test_retrieval_time_is_never_a_historical_availability_proof(tmp_path):
    from quant.data.official_filing_sources import historical_availability
    source = dict(retrieved_at='2024-01-01T16:00:00+05:30', exchange_disseminated_at='2024-01-01T16:00:00+05:30')
    result = historical_availability(source, tmp_path)
    assert result['timing_status'] == 'UNVERIFIED' and result['exchange_disseminated_at'] is None


def test_v2_freeze_rejects_free_text_review_even_with_certified_shared_interval(tmp_path):
    from quant.tests.test_multifactor_engine import reviewed_spec, synthetic_coverage_reports
    from quant.research.specification import freeze_specification
    spec = reviewed_spec()
    reports = synthetic_coverage_reports(spec)
    interval = certify_data_interval(reports['filings'], reports['shares'], matrix=reports['matrix'])
    with pytest.raises(ValueError, match='human governance'):
        freeze_specification(spec, tmp_path/'spec.json', coverage_reports=reports, data_interval=interval)
    assert not list(tmp_path.rglob('spec.json'))


@pytest.mark.parametrize('verified_timing,revision_at', [(False, None), (True, None), (True, '2025-01-01T16:00:00+05:30')])
def test_official_archive_fallback_survives_primary_and_first_document_failures(tmp_path, monkeypatch, verified_timing, revision_at):
    from contextlib import contextmanager
    from quant.config import Config
    from quant.tests.test_evidence_closure import planner_fixture
    from quant.features.tests.test_fundamental_snapshot import filing
    from quant.pipeline.report_fundamental_coverage_ceiling import coverage_ceiling
    from quant.pipeline import discover_fundamentals_targeted as module
    from quant.data.nse_client import RawResponse, NseSourceError
    from quant.storage.research_store import digest_file
    universe, filings, coverage = planner_fixture()
    path = tmp_path/'source.json'
    path.write_text('Synthetic official metadata and document')
    digest = digest_file(path)
    class Blocked:
        last_response = None
        def get_json(self, *a, **k):
            raise NseSourceError('NSE API HTTP 403', http_status=403)
    @contextmanager
    def factory(_):
        yield Blocked()
    class Official:
        def __init__(self, config, source, **kwargs):
            self.source = source
            self.last_response = RawResponse(source['source_url'], '2026-11-19T00:00:00Z', digest, path, 200)
        def close(self):
            pass
    monkeypatch.setattr(module, 'OfficialDocumentClient', Official)
    def archive(client, frame, *args):
        if 'bad' in client.source['source_url']:
            raise OSError('Archive document HTTP 403')
        return frame.assign(parser_status='PARSED', document_sha256=digest, document_raw_path=str(path)), []
    monkeypatch.setattr(module, 'archive_filings', archive)
    sources = []
    for name in ('bad', 'good'):
        row = dict(filing(filing_id=name, instrument_id='c', symbol='C'),
            source_type='NSE_OFFICIAL', source_exchange='NSE',
            source_url=f'https://nsearchives.nseindia.com/{name}.xml',
            dissemination_evidence_path=path.name, dissemination_evidence_sha256=digest,
            dissemination_reviewed_by='SYNTHETIC TEST ONLY' if verified_timing else None,
            period_end=pd.Timestamp('2024-06-30'), revision_at=revision_at)
        sources.append(row)
    result = module.discover_targeted(Config(data_dir=tmp_path), universe, coverage,
        coverage_ceiling(universe, coverage, filings), filings, pd.bdate_range('2024-08-01', '2024-10-31'),
        pd.DataFrame(), client_factory=factory, fallback_manifest=sources, max_requests=3)
    assert len(result['official_route_attempts']) == 2
    assert result['official_route_attempts'][0]['failure'] == 'Archive document HTTP 403'
    if verified_timing and revision_at is None:
        assert result['productivity']['name_month_repairs_per_100_queries'] > 0
    else:
        assert result['productivity']['name_month_repairs_per_100_queries'] == 0
    assert result['official_route_attempts'][1]['review_status'] == ('REVIEWED' if verified_timing else 'NEEDS_REVIEW')


def test_empty_capital_inventory_remains_empty_without_certifying_events(tmp_path):
    from quant.pipeline.verify_capital_events import verify_capital_events
    result = verify_capital_events(pd.DataFrame(), tmp_path)
    assert result.empty and 'verification_status' in result
