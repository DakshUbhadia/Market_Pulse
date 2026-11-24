import pandas as pd
import pytest

from quant.features.fundamental_snapshot import (
    fundamental_snapshot, period_semantics, quarter_only_values, pit_shares_outstanding,
)


def filing(**changes):
    return dict(dict(filing_id='original', instrument_id='a', symbol='A', period_start='2024-04-01',
        period_end='2024-06-30', standalone_or_consolidated='Consolidated', timing_status='VERIFIED',
        parser_status='PARSED', document_sha256='a'*64, revenue=100.,
        exchange_disseminated_at='2024-08-01T16:00:00+05:30', revision_at=None), **changes)


def test_snapshot_uses_exact_publication_and_only_then_known_revision():
    rows = pd.DataFrame([filing(), filing(filing_id='revision', revenue=150., revision_at='2024-08-03T16:00:00+05:30')])
    assert fundamental_snapshot(rows, '2024-08-01T15:59:59+05:30').empty
    assert fundamental_snapshot(rows, '2024-08-01T16:00:00+05:30').revenue.iloc[0] == 100
    assert fundamental_snapshot(rows, '2024-08-03T16:00:00+05:30').revenue.iloc[0] == 150
    with pytest.raises(ValueError, match='timezone'):
        fundamental_snapshot(rows, '2024-08-02')


def test_discovery_metadata_does_not_conflict_with_its_own_parsed_document():
    rows = pd.DataFrame([
        filing(filing_id='metadata', metadata_filing_id='disclosure', parser_status='NEEDS_REVIEW', document_sha256=None),
        filing(filing_id='document', metadata_filing_id='disclosure'),
    ])
    snapshot = fundamental_snapshot(rows, '2024-08-02T16:00:00+05:30')
    assert snapshot.filing_id.tolist() == ['document'] and snapshot.revenue.iloc[0] == 100.
    # A separate document with competing facts cannot be collapsed as metadata.
    conflict = pd.DataFrame([filing(filing_id='conflict', metadata_filing_id='disclosure', document_sha256='b'*64, revenue=999.)])
    assert fundamental_snapshot(pd.concat([rows, conflict]), '2024-08-02T16:00:00+05:30').empty


def test_future_document_cannot_make_discovery_metadata_usable_earlier():
    rows = pd.DataFrame([
        filing(filing_id='metadata', metadata_filing_id='disclosure', parser_status='NEEDS_REVIEW', document_sha256=None),
        filing(filing_id='document', metadata_filing_id='disclosure', revision_at='2024-08-03T16:00:00+05:30'),
    ])
    assert fundamental_snapshot(rows, '2024-08-02T16:00:00+05:30').empty
    assert fundamental_snapshot(rows, '2024-08-04T16:00:00+05:30').filing_id.tolist() == ['document']


def test_unknown_timing_bad_latest_revision_and_ambiguous_revisions_are_unusable():
    for update in [dict(timing_status='UNCERTAIN'), dict(parser_status='NEEDS_REVIEW'), dict(document_sha256=None)]:
        rows = pd.DataFrame([filing(), filing(filing_id='revision', revision_at='2024-08-03T16:00:00+05:30', **update)])
        snapshot = fundamental_snapshot(rows, '2024-08-04T16:00:00+05:30')
        # Unknown timing cannot establish a new revision; known but unusable
        # revisions invalidate the earlier period.
        assert snapshot.empty if 'timing_status' not in update else snapshot.filing_id.tolist() == ['original']
    ambiguous = pd.DataFrame([filing(), filing(filing_id='conflict', revenue=999)])
    assert fundamental_snapshot(ambiguous, '2024-08-04T16:00:00+05:30').empty
    assert fundamental_snapshot(pd.DataFrame([filing(exchange_disseminated_at='2024-08-01 16:00:00')]),
                                '2024-08-04T16:00:00+05:30').empty
    assert fundamental_snapshot(pd.DataFrame([filing(revision_at='2024-08-10 16:00:00')]),
                                '2024-08-04T16:00:00+05:30').empty


def test_periods_and_statement_bases_remain_separate_and_ytd_is_differenced():
    assert period_semantics('2024-04-01','2024-06-30') == 'QUARTER_ONLY'
    assert period_semantics('2024-04-01','2024-09-30') == 'YTD'
    assert period_semantics('2024-04-01','2025-03-31') == 'ANNUAL'
    rows = pd.DataFrame([filing(), filing(filing_id='half', period_end='2024-09-30', revenue=250,
        exchange_disseminated_at='2024-11-01T16:00:00+05:30'), filing(filing_id='standalone',
        standalone_or_consolidated='Standalone', revenue=999)])
    selected = fundamental_snapshot(rows, '2024-11-02T16:00:00+05:30')
    derived = quarter_only_values(selected, ['revenue']).set_index('filing_id')
    assert len(derived) == 2
    assert derived.loc['half','quarter_revenue'] == 150
    missing_q1 = quarter_only_values(selected[selected.filing_id.eq('half')], ['revenue'])
    assert missing_q1.quarter_revenue.isna().all()


def test_shares_never_backfill_current_anchors_and_require_complete_capital_evidence():
    anchors = pd.DataFrame([dict(instrument_id='a', effective_date='2024-06-30', shares_outstanding=100,
        exchange_disseminated_at='2024-08-01T16:00:00+05:30', verification_status='VERIFIED',source_sha256='a'*64)])
    events = pd.DataFrame([dict(instrument_id='a', effective_date='2024-09-01', event_type='SPLIT',
        share_multiplier=2., announced_at='2024-08-20T16:00:00+05:30', verification_status='VERIFIED_COMPLETE',source_sha256='b'*64)])
    assert not pit_shares_outstanding(anchors,events,'a','2024-07-01T16:00:00+05:30', evidence_complete=True)['value_feature_valid']
    assert not pit_shares_outstanding(anchors,events,'a','2024-09-02T16:00:00+05:30')['value_feature_valid']
    result = pit_shares_outstanding(anchors,events,'a','2024-09-02T16:00:00+05:30',evidence_complete=True)
    assert result['value_feature_valid'] and result['shares_outstanding'] == 200
    events.loc[0,'event_type'] = 'MERGER'
    events.loc[0,'share_multiplier'] = float('nan')
    assert not pit_shares_outstanding(anchors,events,'a','2024-09-02T16:00:00+05:30', evidence_complete=True)['value_feature_valid']
    anchors['shares_outstanding'] = 'UNKNOWN'
    assert not pit_shares_outstanding(anchors,pd.DataFrame(),'a','2024-09-02T16:00:00+05:30', evidence_complete=True)['value_feature_valid']


def test_future_share_evidence_cannot_change_earlier_share_snapshot():
    anchors = pd.DataFrame([dict(instrument_id='a',effective_date='2024-06-30',shares_outstanding=100,
        exchange_disseminated_at='2024-08-01T16:00:00+05:30',verification_status='VERIFIED',source_sha256='a'*64)])
    future = pd.DataFrame([dict(instrument_id='a',effective_date='2024-08-15',event_type='ISSUANCE',
        shares_after=150,announced_at='2024-09-01T16:00:00+05:30',verification_status='VERIFIED_COMPLETE',source_sha256='b'*64)])
    before = pit_shares_outstanding(anchors,pd.DataFrame(),'a','2024-08-20T16:00:00+05:30',evidence_complete=True)
    assert before == pit_shares_outstanding(anchors,future,'a','2024-08-20T16:00:00+05:30',evidence_complete=True)
    after = pit_shares_outstanding(anchors,future,'a','2024-09-02T16:00:00+05:30',evidence_complete=True)
    assert after['shares_outstanding'] == 150 and after['value_feature_valid']
