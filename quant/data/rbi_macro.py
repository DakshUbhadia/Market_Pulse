"""Read-only RBI DBIE mirror adapter. Missing release dates are never invented.

The requested rbihub API is a DBIE data mirror. Its latest scrape is not proof
of a historical publication vintage; these rows remain unavailable to historical
backtests unless an actual publication timestamp is supplied by the source.
"""
import json
import re
from pathlib import Path

import numpy as np
import pandas as pd

from quant.data.normalization import csv_frame, keys
from quant.data.http import sha256

REGISTRY_PATH = Path(__file__).with_name('rbi_series_registry.json')


def registry():
    return json.loads(REGISTRY_PATH.read_text(encoding='utf-8'))


def _report_rows(raw, spec):
    if spec['value_column'] not in raw or spec['date_column'] not in raw:
        raise ValueError('RBI report columns changed')
    if not raw[spec['value_column']].str.contains(spec['header'], regex=False).any():
        raise ValueError('RBI report header differs from registry')
    rows = []
    for _, row in raw.iterrows():
        text = str(row[spec['date_column']]).strip()
        if not (re.fullmatch(r'\d{1,2}[-/][A-Za-z0-9]{2,3}[-/]\d{4}', text)
                or re.fullmatch(r'[A-Za-z]{3} \d{1,2}, \d{4}', text)):
            continue
        value = str(row[spec['value_column']]).strip().replace(',', '')
        if value in ('', '-', '--', 'None'):
            continue
        rows.append({'observation_date': pd.to_datetime(text, format='mixed', dayfirst=True),
                     'value': float(value)})
    return pd.DataFrame(rows, columns=['observation_date', 'value'])


def _maturity_rows(raw, spec):
    rows = []
    # Each tab has its own fiscal-year and maturity axes. Never mix tabs.
    for _, group in raw.groupby('tab', sort=False):
        fiscal_year = None
        for _, row in group.sort_values('row_no', key=lambda values: values.astype(int)).iterrows():
            text = str(row['c1']).strip()
            match = re.fullmatch(r'(\d{4})-\d{2,4}', text)
            if match:
                fiscal_year = int(match[1])
                continue
            if text != spec['maturity'] or fiscal_year is None:
                continue
            for i in range(12):
                value = str(row[f'c{i + 2}']).strip()
                if value in ('', '-', '--', 'None'):
                    continue
                month = (i + 3) % 12 + 1
                year = fiscal_year + int(month <= 3)
                rows.append({'observation_date': pd.Timestamp(year, month, 1) + pd.offsets.MonthEnd(),
                             'value': float(value)})
    return pd.DataFrame(rows, columns=['observation_date', 'value']).drop_duplicates()


def parse_macro(content, series, spec, *, url, fetched_at):
    raw = csv_frame(content)
    if spec['parser'] == 'sdmx':
        for name, value in spec['filters'].items():
            if name not in raw:
                raise ValueError(f'Missing RBI dimension {name}')
            raw = raw[raw[name] == value]
        if not {'time_period', 'obs_value'}.issubset(raw.columns):
            raise ValueError('RBI SDMX columns changed')
        frame = raw[['time_period', 'obs_value']].rename(columns={'time_period': 'observation_date', 'obs_value': 'value'})
        frame = frame[~frame.value.isin(['', '-', 'None'])].copy()
        frame['observation_date'] = pd.to_datetime(frame.observation_date, errors='raise')
        frame['value'] = pd.to_numeric(frame.value, errors='raise')
        if 'unit_mult' in raw:
            frame['value'] *= np.power(10.0, pd.to_numeric(raw.loc[frame.index, 'unit_mult'], errors='raise'))
    elif spec['parser'] == 'maturity_matrix':
        frame = _maturity_rows(raw, spec)
    else:
        frame = _report_rows(raw, spec)
        if spec['parser'] == 'credit_growth':
            frame = frame.sort_values('observation_date').drop_duplicates('observation_date').set_index('observation_date')
            if (frame.value <= 0).any():
                raise ValueError('Invalid bank-credit level in source')
            levels = frame.value.to_dict()
            frame['value'] = [100 * (value / levels[day - pd.DateOffset(years=1)] - 1)
                              if day - pd.DateOffset(years=1) in levels else np.nan
                              for day, value in frame.value.items()]
            frame = frame.dropna().reset_index()
    if frame.empty:
        raise ValueError(f'No usable numeric observations from RBI mirror table {spec["table"]}')
    keys(frame, ['observation_date'])
    if not np.isfinite(frame.value).all():
        raise ValueError('Invalid macro observation')
    frame['series'] = series
    frame['unit'] = spec['unit']
    frame['publication_date'] = pd.NaT
    frame['timing_status'] = 'UNCERTAIN'
    frame['first_seen_at'] = pd.Timestamp(fetched_at)
    frame['source_table'] = spec['table'].replace('/', '.')
    frame['source'] = 'RBI_DBIE_RBIHUB_MIRROR'
    frame['source_url'] = url
    frame['source_sha256'] = sha256(content)
    return frame


def available_macro(frame, as_of):
    cutoff = pd.Timestamp(as_of)
    if cutoff.tzinfo is None:
        raise ValueError('as_of must include timezone')
    publication = pd.to_datetime(frame.publication_date, utc=True)
    return frame[(frame.timing_status == 'VERIFIED') & (publication <= cutoff)].copy()
