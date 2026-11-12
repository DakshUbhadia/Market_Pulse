"""Positive trading-session evidence from the official NIFTY history endpoint.

Monthly windows avoid the endpoint's observed truncation of long requests.
Absence of an index row never becomes evidence that a date was a holiday.
"""
import json
from datetime import date, timedelta

import pandas as pd

from quant.data.http import atomic_write, sha256
from quant.data.normalization import records, numeric, dates, keys
from quant.data.nse_client import RawResponse, NseSourceError

PATH = '/api/historicalOR/indicesHistory'
NAMES = {'NIFTY 50', 'S&P CNX NIFTY', 'CNX NIFTY'}


def parse_index_sessions(payload, start, end, raw):
    frame = pd.DataFrame(records(payload))
    mapping = {'EOD_TIMESTAMP': 'trade_date', 'EOD_INDEX_NAME': 'index_name',
               'EOD_OPEN_INDEX_VAL': 'open', 'EOD_HIGH_INDEX_VAL': 'high',
               'EOD_LOW_INDEX_VAL': 'low', 'EOD_CLOSE_INDEX_VAL': 'close'}
    if frame.empty or not set(mapping).issubset(frame.columns):
        raise NseSourceError('No validated NIFTY session history in requested window')
    frame = frame.rename(columns=mapping)
    if not frame.index_name.str.strip().str.upper().isin(NAMES).all():
        raise NseSourceError('Unexpected benchmark in session reconciliation')
    dates(frame, 'trade_date')
    if not frame.trade_date.dt.date.between(start, end).all():
        raise NseSourceError('Index history returned dates outside the requested window')
    numeric(frame, ['open', 'high', 'low', 'close'])
    if ((frame[['open', 'high', 'low', 'close']] <= 0).any().any()
            or (frame.high < frame[['open', 'close', 'low']].max(axis=1)).any()
            or (frame.low > frame[['open', 'close', 'high']].min(axis=1)).any()):
        raise NseSourceError('Invalid benchmark bars in session reconciliation')
    frame = frame.drop_duplicates(list(mapping.values()))
    keys(frame, ['trade_date'])
    return {row.trade_date.date(): raw.provenance() for row in frame.itertuples()}


def fetch_index_sessions(config, client, start, end, today):
    observations, windows = {}, 0
    month = date(start.year, start.month, 1)
    last = min(end, today - timedelta(days=1))
    while month <= last:
        following = (pd.Timestamp(month) + pd.offsets.MonthBegin()).date()
        stop = min(following - timedelta(days=1), last)
        cache = config.data_dir / 'state' / 'calendar_index_sessions' / f'{month:%Y-%m}.json'
        evidence = None
        if cache.exists() and stop < today - timedelta(days=7):
            try:
                info = json.loads(cache.read_text(encoding='utf-8'))
                path = (config.data_dir / info['raw_path']).resolve()
                if (info['base_url'] == config.nse_base_url and info['from'] == str(month)
                        and info['to'] == str(stop) and path.is_relative_to(config.data_dir.resolve())):
                    content = path.read_bytes()
                    if sha256(content) == info['sha256']:
                        raw = RawResponse(info['source_url'], info['fetched_at'], info['sha256'], path, 200)
                        evidence = parse_index_sessions(json.loads(content), month, stop, raw)
            except (ValueError, OSError, KeyError, NseSourceError):
                evidence = None
        if evidence is None:
            payload = client.get_json(PATH, params={'indexType': 'NIFTY 50', 'from': month.strftime('%d-%m-%Y'),
                                                     'to': stop.strftime('%d-%m-%Y')}, dataset='calendar')
            raw = client.last_response
            evidence = parse_index_sessions(payload, month, stop, raw)
            if raw.path.exists() and raw.path.resolve().is_relative_to(config.data_dir.resolve()):
                atomic_write(cache, json.dumps({'base_url': config.nse_base_url, 'from': str(month), 'to': str(stop),
                    'source_url': raw.source_url, 'fetched_at': raw.fetched_at, 'sha256': raw.sha256,
                    'raw_path': str(raw.path.relative_to(config.data_dir))}, indent=2).encode())
        observations.update({day: value for day, value in evidence.items() if start <= day <= end})
        windows += 1
        month = following
    return observations, windows
