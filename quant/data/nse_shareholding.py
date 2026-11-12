"""Shareholding versions are observations, never destructive updates."""
import json

import pandas as pd

from quant.data.normalization import record_id, records
from quant.data.nse_financials import exchange_timestamp
from quant.data.security_history import instrument_id
from quant.data.shareholding_xbrl import CONCEPTS

PATH = '/api/corporate-share-holdings-master'


def parse_shareholding(payload, raw):
    rows = []
    for record in records(payload):
        as_on = record.get('asOnDate') or record.get('date')
        if not record.get('symbol') or not as_on:
            raise ValueError('Shareholding schema changed')
        revision_at = exchange_timestamp(record.get('revisionDate'))
        row = dict(instrument_id=instrument_id(record.get('isin')), symbol=record['symbol'],
                   filing_id=record_id(record), version=record_id(record),
                   as_on_date=pd.to_datetime(as_on, format='mixed').normalize(),
                   submission_date=pd.to_datetime(record.get('submissionDate'), format='mixed').normalize() if record.get('submissionDate') else pd.NaT,
                   revision_date=pd.to_datetime(record.get('revisionDate'), format='mixed').normalize() if record.get('revisionDate') else pd.NaT,
                   revision_at=revision_at,
                   broadcast_at=exchange_timestamp(record.get('broadcastDate')),
                   first_seen_at=pd.Timestamp(raw.fetched_at),
                   source_document=record.get('xbrl') or record.get('xbrlFile'),
                   source_sha256=raw.sha256, source_url=raw.source_url,
                   source_payload=json.dumps(record, sort_keys=True))
        row.update({name: None for name in CONCEPTS})
        broadcast, revision = row['broadcast_at'], revision_at
        row['available_at'] = max(broadcast, revision) if pd.notna(broadcast) and pd.notna(revision) else broadcast
        row['timing_status'] = ('VERIFIED' if pd.notna(broadcast) and not
                                 (record.get('revisionDate') and pd.isna(revision)) else 'UNCERTAIN')
        rows.append(row)
    frame = pd.DataFrame(rows)
    if not frame.empty:
        for name in ('revision_at', 'broadcast_at', 'first_seen_at', 'available_at'):
            frame[name] = pd.to_datetime(frame[name], utc=True)
    return frame


def available_shareholding(frame, as_of):
    cutoff = pd.Timestamp(as_of)
    if cutoff.tzinfo is None:
        raise ValueError('as_of must include timezone')
    if frame.empty:
        return frame.copy()
    at = pd.to_datetime(frame.available_at, utc=True)
    selected = frame[(frame.timing_status == 'VERIFIED') & (at <= cutoff)]
    return selected.sort_values('available_at').drop_duplicates(['instrument_id', 'symbol', 'as_on_date'], keep='last')
