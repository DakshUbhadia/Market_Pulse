"""Batch facade for the existing evidence-only historical-share reconstruction."""
import pandas as pd
from quant.features.fundamental_snapshot import pit_shares_outstanding, aware_times


def share_history(anchors, events, coverage, keys):
    rows = []
    for row in keys.to_dict('records'):
        cutoff = pd.Timestamp(row['signal_timestamp'])
        if cutoff.tzinfo is None:
            raise ValueError('Shares cutoff requires a timezone')
        known_anchors = anchors[anchors.instrument_id.eq(row['instrument_id'])
            & anchors.verification_status.eq('VERIFIED')
            & aware_times(anchors.exchange_disseminated_at).le(cutoff)
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
        rows.append(dict(**row, **result))
    return pd.DataFrame(rows)
