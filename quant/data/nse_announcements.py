"""Preserve exchange announcement records without generating trading signals."""
import json

import pandas as pd

from quant.data.normalization import record_id, records
from quant.data.nse_financials import exchange_timestamp

PATH = '/api/corporate-announcements'


def parse_announcements(payload, raw):
    rows = []
    for record in records(payload):
        if not record.get('symbol') or not record.get('an_dt'):
            raise ValueError('Announcement schema changed')
        timestamp = exchange_timestamp(record.get('exchdisstime') or record['an_dt'])
        if pd.isna(timestamp):
            raise ValueError('Announcement timestamp missing')
        rows.append(dict(symbol=record['symbol'], company=record.get('sm_name'),
                         subject=record.get('desc'), description=record.get('attchmntText'),
                         announcement_timestamp=timestamp, attachment_url=record.get('attchmntFile'),
                         xbrl_url=record.get('xbrl'), source_record_id=str(record.get('seq_id') or record_id(record)),
                         version=record_id(record), source_payload=json.dumps(record, sort_keys=True),
                         source_url=raw.source_url, source_sha256=raw.sha256, first_seen_at=raw.fetched_at))
    return pd.DataFrame(rows)
