"""Reviewed lifecycle evidence; missing publication timing is never inferred."""
import hashlib
import json
import re

import numpy as np
import pandas as pd

PARSER_VERSION = 'lifecycle_1.0.0'
EVENT_TYPES = set('SUSPENSION_ANNOUNCED SUSPENDED DELISTING_ANNOUNCED DELISTED '
    'VOLUNTARY_DELISTING COMPULSORY_DELISTING TENDER_OFFER EXIT_OFFER CASH_SETTLEMENT '
    'MERGER_ANNOUNCED MERGER_EFFECTIVE SHARE_CONVERSION DEMERGER SUCCESSOR_LISTING '
    'RELISTING DISSEMINATION_BOARD SECURITY_CANCELLED ZERO_RECOVERY UNKNOWN'.split())
COLUMNS = ('lifecycle_event_id instrument_id symbol isin event_type announced_at effective_date '
    'last_trading_date record_date settlement_date cash_per_raw_share conversion_ratio '
    'successor_instrument_id offer_start offer_end offer_price mandatory optional source_exchange '
    'source_url source_sha256 raw_path verification_status parser_version first_seen_at').split()


def normalize_events(records):
    rows = []
    for item in records:
        row = {key: item.get(key) for key in COLUMNS}
        row['event_type'] = item.get('event_type', 'UNKNOWN')
        if row['event_type'] not in EVENT_TYPES:
            raise ValueError('Unknown lifecycle event type; use UNKNOWN for ambiguous evidence')
        for key in ('mandatory', 'optional'):
            if item.get(key, False) not in (True, False):
                raise ValueError('Lifecycle flags must be booleans')
            row[key] = bool(item.get(key, False))
        if row['mandatory'] and row['optional']:
            raise ValueError('An event cannot be both mandatory and optional')
        row['announced_at'] = pd.to_datetime(row['announced_at'], utc=True)
        row['first_seen_at'] = pd.to_datetime(row['first_seen_at'], utc=True)
        for key in ('effective_date','last_trading_date','record_date','settlement_date','offer_start','offer_end'):
            row[key] = pd.to_datetime(row[key]).normalize() if row[key] else pd.NaT
        for key in ('cash_per_raw_share','conversion_ratio','offer_price'):
            value = row[key]
            row[key] = float(value) if value is not None else np.nan
            if value is not None and (not np.isfinite(row[key]) or row[key] < 0):
                raise ValueError(f'Invalid lifecycle {key}')
        row['verification_status'] = item.get('verification_status', 'NEEDS_REVIEW')
        if row['verification_status'] == 'VERIFIED':
            if item.get('announced_at') and pd.Timestamp(item['announced_at']).tzinfo is None:
                raise ValueError('Verified publication timing requires an explicit timezone')
            if (not row['instrument_id'] or pd.isna(row['announced_at']) or pd.isna(row['effective_date'])
                    or not row['source_url'] or not row['raw_path'] or not row['source_sha256']
                    or not re.fullmatch('[0-9a-f]{64}',row['source_sha256']) or not row['source_exchange']):
                raise ValueError('Verified lifecycle event requires identity, timing and provenance')
            if row['event_type'] == 'CASH_SETTLEMENT' and (
                    not row['mandatory'] or row['optional'] or pd.isna(row['settlement_date'])
                    or not np.isfinite(row['cash_per_raw_share'])):
                raise ValueError('Cash settlement requires mandatory documented economics')
            if row['event_type'] == 'SHARE_CONVERSION' and (
                    not row['mandatory'] or not row['successor_instrument_id'] or not row['conversion_ratio'] > 0):
                raise ValueError('Conversion requires mandatory successor economics')
        row['parser_version'] = PARSER_VERSION
        row['lifecycle_event_id'] = item.get('lifecycle_event_id') or hashlib.sha256(
            json.dumps(row, sort_keys=True, default=str).encode()).hexdigest()
        rows.append(row)
    result = pd.DataFrame(rows, columns=COLUMNS)
    if result.lifecycle_event_id.duplicated().any():
        raise ValueError('Duplicate lifecycle event IDs')
    return result
