"""Filing metadata, immutable revisions, and strict exchange availability times."""
import json

import pandas as pd

from quant.data.normalization import record_id, records
from quant.data.security_history import instrument_id

PATH = '/api/corporates-financial-results'


def exchange_timestamp(value):
    if not value or value == '-':
        return pd.NaT
    result = pd.Timestamp(pd.to_datetime(value, format='mixed', errors='raise'))
    # A date without a clock time cannot establish point-in-time availability.
    if result.hour == result.minute == result.second == 0 and ':' not in str(value):
        return pd.NaT
    return result.tz_localize('Asia/Kolkata') if result.tzinfo is None else result.tz_convert('Asia/Kolkata')


def parse_financial_filings(payload, raw):
    rows = []
    for record in records(payload):
        if not record.get('symbol') or not record.get('toDate'):
            raise ValueError('Financial filing schema changed')
        disseminated = exchange_timestamp(record.get('exchdisstime') or record.get('disseminationDate'))
        received = exchange_timestamp(record.get('broadCastDate') or record.get('broadcastDate')
                                      or record.get('receivedDate') or record.get('filingDate'))
        revision = exchange_timestamp(record.get('revisionDate'))
        revision_uncertain = bool(record.get('revisionDate')) and pd.isna(revision)
        available = max(disseminated, revision) if pd.notna(disseminated) and pd.notna(revision) else disseminated
        document = record.get('xbrl') or record.get('xbrlFile') or record.get('xbrl_url')
        if document and document.rstrip('/').endswith('/-'):
            document = None
        row = dict(filing_id=record_id(record), version=record_id(record),
                   instrument_id=instrument_id(record.get('isin')), symbol=record['symbol'],
                   period_end=pd.to_datetime(record['toDate'], format='mixed').normalize(),
                   period_start=pd.to_datetime(record['fromDate'], format='mixed').normalize() if record.get('fromDate') else pd.NaT,
                   period_type=record.get('period', 'UNKNOWN'),
                   standalone_or_consolidated=record.get('consolidated', 'UNKNOWN'),
                   bank=True if record.get('bank') == 'Y' else False if record.get('bank') == 'N' else None,
                   exchange_received_at=received, exchange_disseminated_at=disseminated,
                   first_seen_at=pd.Timestamp(raw.fetched_at), revision_at=revision, available_at=available,
                   source_document=document, source_sha256=raw.sha256, source_url=raw.source_url,
                   timing_status='VERIFIED' if pd.notna(disseminated) and not revision_uncertain else 'UNCERTAIN',
                   source_payload=json.dumps(record, sort_keys=True))
        rows.append(row)
    frame = pd.DataFrame(rows)
    if not frame.empty:
        for name in ('exchange_received_at', 'exchange_disseminated_at', 'first_seen_at', 'revision_at', 'available_at'):
            frame[name] = pd.to_datetime(frame[name], utc=True)
    return frame


def available_filings(frame, as_of):
    if frame.empty:
        return frame.copy()
    cutoff = pd.Timestamp(as_of)
    if cutoff.tzinfo is None:
        raise ValueError('as_of must include timezone')
    disseminated = pd.to_datetime(frame.available_at if 'available_at' in frame else frame.exchange_disseminated_at, utc=True)
    selected = frame[(frame.timing_status == 'VERIFIED') & (disseminated <= cutoff)].copy()
    return selected.sort_values('available_at' if 'available_at' in selected else 'exchange_disseminated_at').drop_duplicates(
        ['instrument_id', 'symbol', 'period_end', 'standalone_or_consolidated'], keep='last')
