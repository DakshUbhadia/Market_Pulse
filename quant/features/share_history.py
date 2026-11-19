"""Batch facade for the existing evidence-only historical-share reconstruction."""
import pandas as pd
import numpy as np
from quant.features.fundamental_snapshot import pit_shares_outstanding, number_or_nan


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
    from quant.data.capital_events import reconcile_share_chain
    rows = []
    for row in keys.to_dict('records'):
        cutoff = pd.Timestamp(row['signal_timestamp'])
        if cutoff.tzinfo is None:
            raise ValueError('Shares cutoff requires a timezone')
        chain = reconcile_share_chain(anchors, events, coverage, row['instrument_id'], cutoff)
        if not chain['value_feature_valid']:
            invalid = pit_shares_outstanding(anchors, events, row['instrument_id'], cutoff)
            invalid.update(reason=chain['reason'], share_chain_status=chain['share_chain_status'])
            invalid['share_chain_version'] = chain['share_chain_version']
            invalid.update({k: chain[k] for k in ('replayed_shares', 'reported_shares') if k in chain})
            rows.append(dict(**row, **invalid))
            continue
        result = dict(shares_outstanding=chain['shares_outstanding'], value_feature_valid=True,
            known_at=chain['reconciliation_known_at'], effective_date=chain['reconciliation_anchor_date'],
            source=chain['source'], verification_status='VERIFIED', reason=chain['reason'],
            share_chain_status=chain['share_chain_status'], share_chain_version=chain['share_chain_version'])
        result.update({k: chain[k] for k in ('starting_anchor_date', 'reconciliation_anchor_date', 'reconciliation_known_at')})
        rows.append(dict(**row, **result))
    return pd.DataFrame(rows)
