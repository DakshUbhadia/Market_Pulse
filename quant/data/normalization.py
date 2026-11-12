"""Shared strict source normalization; missing source values stay null."""
import json
from io import BytesIO

import numpy as np
import pandas as pd

from quant.data.http import sha256
from quant.storage.parquet_store import write_parquet

MISSING = ['', '-', '--', 'NA', 'N/A', 'null', None]


def csv_frame(content):
    raw = pd.read_csv(BytesIO(content), dtype=str, keep_default_na=False)
    raw.columns = raw.columns.str.strip().str.lstrip('\ufeff')
    return raw.map(lambda value: value.strip() if isinstance(value, str) else value)


def mapped_csv(content, mapping):
    raw = csv_frame(content)
    missing = set(mapping.values()) - set(raw.columns)
    if missing:
        raise ValueError(f'Missing source columns: {sorted(missing)}')
    return raw.rename(columns={value: key for key, value in mapping.items()})[list(mapping)].copy()


def numeric(frame, columns, *, nullable=(), nonnegative=True):
    for name in columns:
        values = pd.to_numeric(frame[name].mask(frame[name].isin(MISSING)), errors='raise').astype(float)
        present = values.dropna()
        if ((name not in nullable and values.isna().any()) or not np.isfinite(present).all()
                or (nonnegative and (present < 0).any())):
            raise ValueError(f'Invalid numeric {name}')
        frame[name] = values


def keys(frame, columns, *, allow_empty=False):
    if (frame.empty and not allow_empty) or frame[columns].isna().any().any():
        raise ValueError('Empty dataset or missing keys')
    if frame.duplicated(columns).any():
        raise ValueError(f'Duplicate keys: {columns}')
    if any(frame[name].astype(str).str.strip().eq('').any() for name in columns):
        raise ValueError('Empty key')


def dates(frame, name, *, expected=None, nullable=False):
    frame[name] = pd.to_datetime(frame[name].mask(frame[name].isin(MISSING)), format='mixed',
                                 dayfirst=True, errors='raise').dt.normalize()
    if not nullable and frame[name].isna().any():
        raise ValueError(f'Missing {name}')
    if expected is not None and not frame[name].dt.date.eq(expected).all():
        raise ValueError('Source date differs from requested date')


def provenance(frame, content, url):
    frame['source_url'] = url
    frame['source_sha256'] = sha256(content)
    frame['source'] = 'NSE'
    return frame


def record_id(record):
    return sha256(json.dumps(record, sort_keys=True, ensure_ascii=False, default=str).encode())


def records(payload):
    if isinstance(payload, dict) and isinstance(payload.get('data'), list):
        payload = payload['data']
    if not isinstance(payload, list) or any(not isinstance(row, dict) for row in payload):
        raise ValueError('Source must contain a record array')
    return payload


def write_daily(frame, root, date_column='trade_date'):
    paths = []
    for day, group in frame.groupby(date_column):
        day = pd.Timestamp(day)
        paths.append(write_parquet(group, root / f'year={day.year}' / f'month={day.month:02d}'
                                   / f'{day:%Y-%m-%d}.parquet'))
    return paths


def write_observation(frame, root, digest, observed_at):
    """Keep each response version. Repeated observations are deduplicated by content."""
    if frame.empty:
        return None
    at = pd.Timestamp(observed_at)
    path = root / f'year={at.year}' / f'month={at.month:02d}' / f'{digest}.parquet'
    frame = frame.copy()
    if path.exists() and 'first_seen_at' in frame:
        previous = pd.read_parquet(path)
        identity = next((key for key in ('filing_id', 'event_id', 'source_record_id', 'version') if key in frame and key in previous), None)
        if identity and 'first_seen_at' in previous:
            first = previous.groupby(identity).first_seen_at.min()
            frame['first_seen_at'] = pd.to_datetime(frame[identity].map(first).fillna(frame.first_seen_at), utc=True)
    frame['parser_version'] = 'foundation-1'
    # Normalized data can be rebuilt when parsing improves; raw response versions
    # and distinct filing-version files remain immutable.
    write_parquet(frame, path)
    return path
