"""Monthly official benchmark requests, including pre-daily-archive history."""
import json
from datetime import date, timedelta

import pandas as pd

from quant.data.http import atomic_write, sha256
from quant.data.nse_client import NseClient
from quant.data.normalization import records, numeric, dates, keys
from quant.pipeline.update_market_eod import daily_path
from quant.storage.parquet_store import write_parquet

ALIASES = {'NIFTY 50': {'NIFTY 50', 'CNX NIFTY', 'S&P CNX NIFTY'},
           'NIFTY 500': {'NIFTY 500', 'CNX 500', 'S&P CNX 500'}}


def parse_history(payload, name, start, end, metadata):
    raw = pd.DataFrame(records(payload))
    mapping = dict(trade_date='EOD_TIMESTAMP', index_name='EOD_INDEX_NAME', open='EOD_OPEN_INDEX_VAL',
                   high='EOD_HIGH_INDEX_VAL', low='EOD_LOW_INDEX_VAL', close='EOD_CLOSE_INDEX_VAL')
    if raw.empty or not set(mapping.values()).issubset(raw.columns):
        raise ValueError(f'No {name} historical data')
    frame = raw.rename(columns={v: k for k, v in mapping.items()})[list(mapping)].copy()
    if not frame.index_name.str.upper().str.strip().isin(ALIASES[name]).all():
        raise ValueError('Unexpected benchmark name')
    frame['index_name'] = name
    dates(frame, 'trade_date')
    if not frame.trade_date.dt.date.between(start, end).all():
        raise ValueError('Benchmark dates outside requested monthly window')
    numeric(frame, ['open', 'high', 'low', 'close'])
    if ((frame[['open', 'high', 'low', 'close']] <= 0).any().any()
            or (frame.high < frame[['open', 'close', 'low']].max(axis=1)).any()
            or (frame.low > frame[['open', 'close', 'high']].min(axis=1)).any()):
        raise ValueError('Invalid historical benchmark OHLC')
    keys(frame, ['trade_date', 'index_name'])
    frame['shares_traded'] = pd.to_numeric(raw.get('HIT_TRADED_QTY'), errors='coerce')
    frame['turnover'] = pd.to_numeric(raw.get('HIT_TURN_OVER'), errors='coerce') * 10_000_000
    frame['source'] = 'NSE'
    frame['source_url'] = metadata['source_url']
    frame['source_sha256'] = metadata['sha256']
    frame['data_quality'] = 'OK'
    return frame


def backfill_benchmarks(config, start, end):
    month = date(start.year, start.month, 1)
    with NseClient(config) as client:
        while month <= end:
            following = (pd.Timestamp(month) + pd.offsets.MonthBegin()).date()
            stop = min(end, following - timedelta(days=1))
            blocks = []
            for name in ALIASES:
                cache = (config.data_dir / 'state' / ('calendar_index_sessions' if name == 'NIFTY 50'
                         else 'benchmark_nifty500') / f'{month:%Y-%m}.json')
                payload = info = None
                if cache.exists():
                    try:
                        info = json.loads(cache.read_text())
                        path = (config.data_dir / info['raw_path']).resolve()
                        if (info['from'] == str(month) and info['to'] == str(stop)
                                and path.is_relative_to(config.data_dir.resolve())):
                            content = path.read_bytes()
                            if sha256(content) == info['sha256']:
                                payload = json.loads(content)
                    except (OSError, ValueError, KeyError):
                        payload = None
                if payload is None:
                    payload = client.get_json('/api/historicalOR/indicesHistory', params={'indexType': name,
                        'from': month.strftime('%d-%m-%Y'), 'to': stop.strftime('%d-%m-%Y')}, dataset='indices')
                    raw = client.last_response
                    info = dict(source_url=raw.source_url, sha256=raw.sha256, fetched_at=raw.fetched_at,
                        raw_path=str(raw.path.relative_to(config.data_dir)), **{'from': str(month), 'to': str(stop)})
                frame = parse_history(payload, name, month, stop, info)
                atomic_write(cache, json.dumps(info, indent=2).encode())
                blocks.append(frame[frame.trade_date.dt.date >= start])
            for day, group in pd.concat(blocks).groupby('trade_date'):
                path = daily_path(config, 'indices', day.date())
                if path.exists():
                    old = pd.read_parquet(path)
                    group = pd.concat([old[~old.index_name.isin(ALIASES)], group], ignore_index=True)
                write_parquet(group, path)
            print(f'{month:%Y-%m}: benchmark history normalized', flush=True)
            month = following


def main():
    from quant.pipeline.cli import parser_config
    parser, config = parser_config(__doc__)
    args = parser.parse_args()
    backfill_benchmarks(args.config(config), args.start, args.end)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
