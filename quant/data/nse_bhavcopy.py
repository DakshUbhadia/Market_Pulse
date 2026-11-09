"""Normalize legacy and UDiFF cash bhavcopies without adjusting prices."""
from datetime import date
from io import BytesIO
from zipfile import ZipFile

import numpy as np
import pandas as pd

from quant.data.http import sha256

TRANSITION = date(2024, 7, 8)
MONTHS = ('JAN', 'FEB', 'MAR', 'APR', 'MAY', 'JUN', 'JUL', 'AUG', 'SEP', 'OCT', 'NOV', 'DEC')
LEGACY = dict(trade_date='TIMESTAMP', symbol='SYMBOL', series='SERIES', isin='ISIN',
              open='OPEN', high='HIGH', low='LOW', close='CLOSE', last='LAST',
              previous_close='PREVCLOSE', volume='TOTTRDQTY', traded_value='TOTTRDVAL',
              num_trades='TOTALTRADES')
UDIFF = dict(trade_date='TradDt', symbol='TckrSymb', series='SctySrs', isin='ISIN',
             open='OpnPric', high='HghPric', low='LwPric', close='ClsPric', last='LastPric',
             previous_close='PrvsClsgPric', volume='TtlTradgVol', traded_value='TtlTrfVal',
             num_trades='TtlNbOfTxsExctd')
NUMERIC = ('open', 'high', 'low', 'close', 'last', 'previous_close', 'volume', 'traded_value')
KEY = ['trade_date', 'symbol', 'series']


def source_url(day: date) -> str:
    base = 'https://nsearchives.nseindia.com/content/'
    if day >= TRANSITION:
        return f'{base}cm/BhavCopy_NSE_CM_0_0_0_{day:%Y%m%d}_F_0000.csv.zip'
    month = MONTHS[day.month - 1]
    return f'{base}historical/EQUITIES/{day.year}/{month}/cm{day.day:02d}{month}{day.year}bhav.csv.zip'


def validate_bars(frame: pd.DataFrame) -> None:
    if frame.empty:
        raise ValueError('Bhavcopy has no rows')
    if frame[KEY].isna().any().any() or frame.duplicated(KEY).any():
        raise ValueError('Missing or duplicate date/symbol/series keys')
    if (frame['symbol'] == '').any():
        raise ValueError('Empty symbol')
    values = frame[[c for c in NUMERIC if c != 'last']].to_numpy(dtype=float)
    if not np.isfinite(values).all() or (values < 0).any():
        raise ValueError('Invalid numeric values')
    if (frame['close'] <= 0).any():
        raise ValueError('Nonpositive close')
    last = frame['last'].dropna().to_numpy(dtype=float)
    if not np.isfinite(last).all() or (last < 0).any():
        raise ValueError('Invalid last price')
    # Some nontraded securities have zero OHLC; retain but never make them eligible here.
    traded = frame['volume'] > 0
    bars = frame.loc[traded]
    if ((bars[['open', 'high', 'low']] <= 0).any().any()
            or (bars['high'] < bars[['open', 'close', 'low']].max(axis=1)).any()
            or (bars['low'] > bars[['open', 'close', 'high']].min(axis=1)).any()):
        raise ValueError('Inconsistent OHLC prices')
    for name in ('volume', 'num_trades'):
        values = frame[name].dropna()
        if ((values < 0) | (values % 1 != 0)).any():
            raise ValueError(f'Invalid integer {name}')


def parse_bhavcopy(content: bytes, day: date, url: str | None = None) -> pd.DataFrame:
    with ZipFile(BytesIO(content)) as archive:
        csvs = [entry for entry in archive.infolist() if entry.filename.lower().endswith('.csv')]
        if len(csvs) != 1 or csvs[0].file_size > 100_000_000:
            raise ValueError('Expected one CSV smaller than 100 MB')
        raw = pd.read_csv(BytesIO(archive.read(csvs[0])), dtype=str, keep_default_na=False)
    raw.columns = raw.columns.str.strip().str.lstrip('\ufeff')
    mapping = LEGACY if day < TRANSITION else UDIFF
    required = set(mapping.values()) - {mapping['num_trades'], mapping['isin']}
    missing = required - set(raw.columns)
    if missing:
        raise ValueError(f'Missing bhavcopy columns: {sorted(missing)}')
    frame = pd.DataFrame({name: raw[column].str.strip() if column in raw else pd.NA
                          for name, column in mapping.items()})
    frame['trade_date'] = pd.to_datetime(frame['trade_date'], format='mixed', errors='raise').dt.normalize()
    if not (frame['trade_date'].dt.date == day).all():
        raise ValueError('File trade date does not match requested date')
    for column in NUMERIC:
        frame[column] = pd.to_numeric(frame[column].replace('', float('nan')), errors='raise').astype('float64')
    frame['num_trades'] = pd.to_numeric(frame['num_trades'].replace('', pd.NA), errors='raise').astype('Int64')
    frame['volume'] = frame['volume'].astype('float64')
    frame['source_file'] = url or source_url(day)
    frame['source_hash'] = sha256(content)
    frame['data_quality'] = np.where(frame['series'] == '', 'MISSING_SERIES',
                                     np.where(frame['last'].isna(), 'MISSING_LAST', 'OK'))
    validate_bars(frame)
    frame['volume'] = frame['volume'].astype('int64')
    return frame.sort_values(KEY).reset_index(drop=True)
