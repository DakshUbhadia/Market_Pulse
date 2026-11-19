"""Discovery and share certification must fail closed without real evidence."""
from contextlib import contextmanager
from types import SimpleNamespace

import pandas as pd
import pytest

from quant.config import Config
from quant.data.capital_events import capital_event_ledger, replay_capital_event, reconcile_share_chain, EVENT_TYPES
from quant.data.fundamental_discovery_gap import build_discovery_gap, select_discovery_batch
from quant.data.official_filing_sources import validate_official_source
from quant.features.share_history import share_history
from quant.pipeline.report_fundamental_coverage_ceiling import coverage_ceiling
from quant.tests.test_evidence_closure import planner_fixture
from quant.forward.signal_store import content_hash


def test_discovery_ledger_keeps_the_missing_workload_and_never_uses_future_returns():
    universe, filings, coverage = planner_fixture()
    ceiling = coverage_ceiling(universe, coverage, filings)
    ledger = build_discovery_gap(universe, coverage, ceiling, filings)
    assert ledger['missing_cells'] == 4 and ledger['missing_instruments'] == 2
    first = next(r for r in ledger['cells'] if r['instrument_id'] == 'c')
    assert not first['candidate_present'] and not first['candidate_url_present']
    assert first['gap_reason'] == 'NO_KNOWN_CANDIDATE'
    assert first['required_statement_basis'] == 'CONSOLIDATED'
    assert first['source_hierarchy'] == ['NSE_OFFICIAL', 'BSE_OFFICIAL', 'ISSUER_IR']
    universe['future_return'], filings['future_return'] = 10000, -10000
    assert build_discovery_gap(universe, coverage, ceiling, filings) == ledger
    batch = select_discovery_batch(ledger, max_instruments=1, max_cells=2)
    assert len(batch) == 2 and len({r['instrument_id'] for r in batch}) == 1
    ledger['cells'][0]['priority'] = 999
    with pytest.raises(ValueError, match='checksum'):
        select_discovery_batch(ledger)


@pytest.mark.parametrize('limits', [dict(max_cells=101), dict(max_instruments=51), dict(max_cells=0)])
def test_discovery_batch_is_bounded(limits):
    with pytest.raises(ValueError, match='batches'):
        select_discovery_batch(dict(cells=[], sha256=content_hash([])), **limits)


@pytest.mark.parametrize('kind,fields,expected', [
    ('SPLIT', dict(share_multiplier=2), 200), ('BONUS', dict(share_multiplier=1.5), 150),
    ('BUYBACK', dict(shares_removed=20), 80), ('RIGHTS_ISSUE', dict(shares_added=10), 110),
    ('PUBLIC_ISSUE', dict(shares_added=10), 110), ('PRIVATE_PLACEMENT', dict(shares_added=10), 110),
    ('ESOP_ISSUANCE', dict(shares_added=10), 110), ('MERGER_CONVERSION', dict(share_multiplier=2), 200),
    ('DEMERGER_ALLOCATION', dict(shares_added=10), 110), ('CAPITAL_REDUCTION', dict(shares_removed=50), 50),
    ('FACE_VALUE_CHANGE', dict(share_multiplier=2), 200)])
def test_capital_event_arithmetic(kind, fields, expected):
    assert replay_capital_event(100, dict(event_type=kind, **fields)) == expected


@pytest.mark.parametrize('fields', [dict(shares_after=120), dict(shares_added=-2),
    dict(shares_added=float('inf')), dict(shares_added=10, shares_after=120)])
def test_after_count_does_not_force_event_equality(fields):
    with pytest.raises(ValueError):
        replay_capital_event(100, dict(event_type='PUBLIC_ISSUE', **fields))


def chain_inputs():
    anchors = pd.DataFrame([dict(instrument_id='a', effective_date=d, shares_outstanding=s,
        exchange_disseminated_at=t, source_sha256=h*64, verification_status='VERIFIED')
        for d, s, t, h in [('2024-03-31', 100, '2024-04-01T16:00:00+05:30', 'a'),
                           ('2024-06-30', 220, '2024-07-01T16:00:00+05:30', 'b')]])
    events = pd.DataFrame([dict(instrument_id='a', effective_date=d, event_type=k,
        announced_at='2024-04-02T16:00:00+05:30', verification_status='VERIFIED', source_sha256='c'*64, **f)
        for d, k, f in [('2024-04-15', 'SPLIT', dict(share_multiplier=2)),
                        ('2024-05-15', 'ESOP_ISSUANCE', dict(shares_added=20))]])
    coverage = pd.DataFrame([dict(instrument_id='a', covered_from='2024-03-31', covered_through='2024-08-30',
        known_at='2024-08-30T15:00:00+05:30', source_sha256='d'*64, verification_status='VERIFIED')])
    return anchors, events, coverage


def test_chain_requires_later_reconciliation_and_all_material_events():
    anchors, events, coverage = chain_inputs()
    cutoff = '2024-08-30T15:30:00+05:30'
    result = reconcile_share_chain(anchors, events, coverage, 'a', cutoff)
    assert result['share_chain_status'] == 'VERIFIED_COMPLETE' and result['shares_outstanding'] == 220
    assert not reconcile_share_chain(anchors.iloc[:1], events, coverage, 'a', cutoff)['value_feature_valid']
    broken = reconcile_share_chain(anchors, events.iloc[:1], coverage, 'a', cutoff)
    assert broken['share_chain_status'] == 'BROKEN' and broken['reason'] == 'UNEXPLAINED_ANCHOR_MISMATCH'
    keys = pd.DataFrame([dict(instrument_id='a', signal_timestamp=cutoff)])
    assert share_history(anchors, events, coverage, keys).value_feature_valid.iloc[0]
    assert not share_history(anchors, events.iloc[:1], coverage, keys).value_feature_valid.iloc[0]


def test_reconciliation_cannot_leak_later_knowledge_or_erase_an_earlier_mismatch():
    anchors, events, coverage = chain_inputs()
    cutoff = '2024-08-30T15:30:00+05:30'
    future = anchors.copy()
    future.loc[1, 'exchange_disseminated_at'] = '2024-09-01T12:00:00+05:30'
    assert not reconcile_share_chain(future, events, coverage, 'a', cutoff)['value_feature_valid']
    middle = anchors.iloc[[0]].assign(effective_date='2024-04-30', shares_outstanding=150,
                                     exchange_disseminated_at='2024-05-01T12:00:00+05:30')
    result = reconcile_share_chain(pd.concat([anchors, middle]), events, coverage, 'a', cutoff)
    assert result['share_chain_status'] == 'BROKEN'
    coverage['known_at'] = '2024-09-01T12:00:00+05:30'
    assert not reconcile_share_chain(anchors, events, coverage, 'a', cutoff)['value_feature_valid']


def test_capital_ledger_does_not_invent_terms_or_verify_unarchived_bytes(tmp_path):
    from quant.pipeline.audit_share_history_coverage import verify_share_archives
    anchors, events, _ = chain_inputs()
    events['security_lineage_id'], events['source_url'] = 'line-a', 'https://www.nseindia.com/evidence'
    ledger = capital_event_ledger(events)
    assert len(ledger) == 2 and set(ledger.event_type).issubset(EVENT_TYPES)
    assert verify_share_archives(ledger, tmp_path).verification_status.eq('NEEDS_REVIEW').all()
    duplicated = pd.concat([events, events.iloc[[0]].assign(event_type='BONUS', share_multiplier=1.5)])
    assert capital_event_ledger(duplicated).verification_status.eq('NEEDS_REVIEW').sum() == 2


def test_action_candidates_do_not_assume_ex_date_is_a_share_effective_date():
    from quant.data.capital_events import capital_candidates_from_actions
    actions = pd.DataFrame([dict(event_id=str(i), instrument_id='a', action_type='BONUS',
        ex_date=d, record_date=d, ratio_numerator=1, ratio_denominator=1,
        parse_status='PARSED', source_url='https://www.nseindia.com/evidence', source_sha256='a'*64)
        for i, d in enumerate(['2024-04-01', '2024-05-01'])])
    candidates = capital_event_ledger(capital_candidates_from_actions(actions))
    assert len(candidates) == 2 and candidates.effective_date.isna().all()
    assert candidates.announced_at.isna().all() and candidates.share_multiplier.eq(2).all()
    assert candidates.verification_status.eq('NEEDS_REVIEW').all()


def test_capital_event_without_a_later_anchor_cannot_validate_value():
    anchors, events, coverage = chain_inputs()
    tail = events.iloc[[0]].assign(effective_date='2024-07-15')
    result = reconcile_share_chain(anchors, pd.concat([events, tail]), coverage, 'a', '2024-08-30T15:30:00+05:30')
    assert result['reason'] == 'LATER_ANCHOR_REQUIRED_AFTER_CAPITAL_EVENT'
    assert not result['value_feature_valid']


def test_official_fallback_requires_primary_failure_identity_and_review():
    source = dict(source_type='BSE_OFFICIAL', source_exchange='BSE', source_url='https://www.bseindia.com/a.xml')
    with pytest.raises(ValueError, match='reason'):
        validate_official_source(source)
    source['reason_primary_source_unavailable'] = 'Archived NSE response HTTP 403'
    with pytest.raises(ValueError, match='cross-listed'):
        validate_official_source(source)
    source.update(cross_listing_verified=True, bse_security_code='500000')
    assert validate_official_source(source) == source
    source.update(source_type='ISSUER_IR', source_exchange=None, source_url='https://issuer.example/a.xml')
    with pytest.raises(ValueError):
        validate_official_source(source, issuer_hosts=['issuer.example'])
    source.update(issuer_host_reviewed_by='test reviewer', reason_exchange_archive_unavailable='Both archives unavailable')
    assert validate_official_source(source, issuer_hosts=['issuer.example']) == source
    source['source_url'] = 'https://aggregator.example/a.xml'
    with pytest.raises(ValueError):
        validate_official_source(source, issuer_hosts=['issuer.example'])


def test_blocked_discovery_archives_batch_and_replans_without_claiming_gains(tmp_path):
    from quant.data.nse_client import NseSourceError
    from quant.pipeline.discover_fundamentals_targeted import discover_targeted
    universe, filings, coverage = planner_fixture()
    ceiling = coverage_ceiling(universe, coverage, filings)
    calls = []
    class Blocked:
        last_response = None
        def get_json(self, *args, **kwargs):
            calls.append(kwargs)
            raise NseSourceError('NSE warm-up HTTP 403', http_status=403)
    @contextmanager
    def factory(_):
        yield Blocked()
    report = discover_targeted(Config(data_dir=tmp_path), universe, coverage, ceiling, filings,
        pd.bdate_range('2024-08-01', '2024-10-31'), pd.DataFrame(), client_factory=factory)
    assert report['status'] == 'SOURCE_BLOCKED' and len(calls) == 1
    assert report['missing_cells_before'] == report['missing_cells_after'] == 4
    assert report['new_observations'] == 0 and not report['coverage_certified']
    assert (tmp_path/'research/discovery-batches').exists()


def test_next_bounded_batch_continues_after_completed_empty_queries(tmp_path):
    import json
    from quant.data.nse_client import RawResponse
    from quant.storage.research_store import digest_file
    from quant.pipeline.discover_fundamentals_targeted import discover_targeted
    universe, filings, coverage = planner_fixture()
    ceiling = coverage_ceiling(universe, coverage, filings)
    payload = tmp_path/'response.json'
    payload.write_bytes(b'[]')
    queries = []
    class Empty:
        last_response = RawResponse('https://www.nseindia.com/api/corporates-financial-results',
            '2026-11-19T12:00:00+05:30', digest_file(payload), payload, 200)
        def get_json(self, *args, **kwargs):
            queries.append(kwargs['params'])
            return []
    @contextmanager
    def factory(_):
        yield Empty()
    kwargs = dict(config=Config(data_dir=tmp_path), universe=universe, coverage=coverage,
        ceiling=ceiling, filings=filings, sessions=pd.bdate_range('2024-08-01', '2024-10-31'),
        history=pd.DataFrame(), max_requests=1, client_factory=factory)
    first = discover_targeted(**kwargs)
    second = discover_targeted(**kwargs, completed_queries=first['responses'])
    assert first['requests'] == second['requests'] == 1
    assert second['completed_queries_skipped'] == 1
    assert queries[0]['period'] == 'Annual' and queries[1]['period'] == 'Quarterly'
    payload.write_bytes(b'changed')
    with pytest.raises(ValueError, match='Previous discovery evidence'):
        discover_targeted(**kwargs, completed_queries=first['responses'])


def test_successful_batch_reaudits_gain_and_does_not_invent_unattempted_downloads(tmp_path, monkeypatch):
    import json
    from pathlib import Path
    from quant.data.nse_client import RawResponse
    from quant.features.tests.test_fundamental_snapshot import filing
    from quant.storage.research_store import digest_file
    from quant.storage.parquet_store import read_parquet_file
    from quant.pipeline import discover_fundamentals_targeted as module
    universe, filings, coverage = planner_fixture()
    ceiling = coverage_ceiling(universe, coverage, filings)
    payload = tmp_path/'source.json'
    payload.write_bytes(b'synthetic official response')
    digest = digest_file(payload)
    raw = RawResponse('https://www.nseindia.com/api/corporates-financial-results',
        '2026-11-19T12:00:00+05:30', digest, payload, 200)
    metadata = pd.DataFrame([filing(filing_id='new-c-'+str(i), instrument_id='c', symbol='C',
        source_document='https://nsearchives.nseindia.com/'+str(i)+'.xml',
        document_sha256=None, metadata_raw_path=str(payload), source_sha256=digest,
        period_start='2024-04-01' if i == 0 else '2023-04-01',
        period_end='2024-06-30' if i == 0 else '2024-03-31') for i in range(2)])
    class Found:
        last_response = raw
        def get_json(self, *a, **k):
            return []
    @contextmanager
    def factory(_):
        yield Found()
    monkeypatch.setattr(module, 'parse_financial_filings', lambda *a: metadata.copy())
    def parsed(client, frame, *a):
        return frame.assign(document_sha256=digest, document_raw_path=str(payload), parser_status='PARSED'), []
    monkeypatch.setattr(module, 'archive_filings', parsed)
    result = module.discover_targeted(Config(data_dir=tmp_path), universe, coverage, ceiling, filings,
        pd.bdate_range('2024-08-01', '2024-10-31'), pd.DataFrame(), max_requests=1,
        max_documents=1, client_factory=factory)
    assert result['documents_attempted'] == 1 and result['new_observations'] == 2
    assert result['missing_cells_after'] < result['missing_cells_before']
    root = Path(result['output'])
    attempts = json.loads((root/'attempts.json').read_text())['attempted']
    assert set(attempts) == {'new-c-0'}
    added = read_parquet_file(root/'new-filings.parquet')
    assert added.loc[added.metadata_filing_id.eq('new-c-1'), 'parser_status'].iloc[0] == 'NOT_ATTEMPTED'


def test_missing_local_unit_evidence_cannot_certify_even_with_remote_success(tmp_path, monkeypatch):
    from quant.pipeline import certify_implementation as module
    monkeypatch.setattr(module, 'git_commit', lambda: 'a'*40)
    monkeypatch.setattr(module, 'local_checks', lambda: {k:dict(status='PASS') for k in
        ('dependency_check', 'compile_check', 'whitespace_check')})
    monkeypatch.setattr(module.subprocess, 'run', lambda *a, **k: SimpleNamespace(stdout=''))
    runs = [dict(name='Quant unit tests', head_sha='a'*40, status='completed', conclusion='success')]
    client = SimpleNamespace(get=lambda *a, **k: SimpleNamespace(raise_for_status=lambda: None,
        json=lambda: dict(workflow_runs=runs)))
    assert module.certify_implementation(Config(data_dir=tmp_path), session=client)['status'] == 'NOT_CERTIFIED'


def test_historical_entry_preserves_and_checks_the_certified_junit_bytes(tmp_path, monkeypatch):
    from quant.pipeline import certify_implementation as module
    from quant.storage.research_store import digest_file, write_json
    sha = 'a'*40
    junit = tmp_path/'unit.xml'
    junit.write_text('<testsuite><testcase name="unit"/></testsuite>')
    prior = dict(git_commit=sha, RESEARCH_CERTIFIED_SHA=sha, unit_results_path=str(junit.resolve()),
        local_test_evidence={str(junit): digest_file(junit)})
    write_json(tmp_path/'reports/implementation-certification.json', prior)
    monkeypatch.setattr(module, 'git_commit', lambda: sha)
    def fresh(config, **kwargs):
        assert kwargs['unit_results'] == junit.resolve()
        return dict(status='CERTIFIED', RESEARCH_CERTIFIED_SHA=sha)
    monkeypatch.setattr(module, 'certify_implementation', fresh)
    assert module.require_certified_implementation(Config(data_dir=tmp_path))['RESEARCH_CERTIFIED_SHA'] == sha
    junit.write_text('changed')
    with pytest.raises(ValueError, match='JUnit evidence'):
        module.require_certified_implementation(Config(data_dir=tmp_path))
