"""Batch facade for the existing evidence-only historical-share reconstruction."""
import pandas as pd
import numpy as np
from quant.features.fundamental_snapshot import pit_shares_outstanding, aware_times, number_or_nan, evidence_known_times


def derive_share_anchors(filings):
    """Paid-up equity capital / contemporaneous face value, in normalized INR units.

    These anchors still require archived-byte verification and a complete capital
    event interval. Current security-master share counts are never an input.
    """
    columns = ['instrument_id', 'shares_outstanding', 'exchange_disseminated_at', 'known_at',
               'effective_date', 'source', 'source_sha256', 'raw_path', 'verification_status']
    rows = []
    for row in filings.to_dict('records'):
        capital, face = (number_or_nan(row.get(k)) for k in ('paid_up_capital', 'face_value'))
        stamps = [pd.Timestamp(row[k]) for k in ('exchange_disseminated_at', 'available_at', 'revision_at') if pd.notna(row.get(k))]
        if (row.get('parser_status') != 'PARSED' or row.get('timing_status') != 'VERIFIED'
                or not row.get('instrument_id') or not np.isfinite(capital) or not np.isfinite(face)
                or capital <= 0 or face <= 0 or not stamps or any(s.tzinfo is None for s in stamps)
                or pd.isna(row.get('period_end')) or pd.notna(row.get('document_revision_detected_at'))):
            continue
        known = max(stamps)
        rows.append(dict(instrument_id=row['instrument_id'], shares_outstanding=capital/face,
            exchange_disseminated_at=known.isoformat(), known_at=known.isoformat(), effective_date=str(pd.Timestamp(row['period_end']).date()),
            source=row.get('source_document'), source_sha256=row.get('document_sha256'),
            raw_path=row.get('document_raw_path'), verification_status='VERIFIED'))
    return pd.DataFrame(rows, columns=columns).drop_duplicates()


def share_history(anchors, events, coverage, keys):
    rows = []
    for row in keys.to_dict('records'):
        cutoff = pd.Timestamp(row['signal_timestamp'])
        if cutoff.tzinfo is None:
            raise ValueError('Shares cutoff requires a timezone')
        if coverage.empty or anchors.empty:
            rows.append(dict(**row, **pit_shares_outstanding(anchors, events, row['instrument_id'], cutoff)))
            continue
        known_anchors = anchors[anchors.instrument_id.eq(row['instrument_id'])
            & anchors.verification_status.eq('VERIFIED')
            & evidence_known_times(anchors, 'exchange_disseminated_at').le(cutoff)
            & pd.to_datetime(anchors.effective_date).le(cutoff.tz_convert('Asia/Kolkata').tz_localize(None).normalize())] if not anchors.empty else anchors
        anchor_date = pd.to_datetime(known_anchors.effective_date).max() if not known_anchors.empty else pd.NaT
        verified = coverage[coverage.instrument_id.eq(row['instrument_id'])
            & coverage.verification_status.eq('VERIFIED')
            & aware_times(coverage.known_at).le(cutoff)
            & coverage.source_sha256.astype('string').str.fullmatch('[0-9a-f]{64}',na=False)
            & pd.to_datetime(coverage.covered_from).le(anchor_date)
            & pd.to_datetime(coverage.covered_through).ge(cutoff.tz_convert('Asia/Kolkata').tz_localize(None).normalize())] if not coverage.empty else coverage
        result = pit_shares_outstanding(anchors, events, row['instrument_id'], cutoff,
                                       evidence_complete=bool(len(verified)))
        if result['value_feature_valid']:
            proof = verified.sort_values('known_at').iloc[-1]
            result['known_at'] = max(pd.Timestamp(result['known_at']), pd.Timestamp(proof.known_at)).isoformat()
            result['source'] = sorted(set(result['source']+[proof.source_sha256]))
        rows.append(dict(**row, **result))
    return pd.DataFrame(rows)
