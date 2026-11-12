"""Evidence-based symbol intervals; never resolve identity using company names."""
import re
from uuid import NAMESPACE_URL, uuid5

import pandas as pd


def instrument_id(isin):
    if not isinstance(isin, str) or not re.fullmatch(r'IN[A-Z0-9]{10}', isin.strip()):
        return None
    return str(uuid5(NAMESPACE_URL, 'isin:' + isin.strip()))


def build_security_history(observations):
    columns = ['instrument_id', 'isin', 'symbol', 'series', 'valid_from', 'valid_to', 'identity_status']
    if observations.empty:
        return pd.DataFrame(columns=columns)
    frame = observations[['trade_date', 'symbol', 'series', 'isin']].copy()
    frame['trade_date'] = pd.to_datetime(frame.trade_date).dt.normalize()
    frame['isin'] = frame['isin'].fillna('').str.strip()
    frame = frame.drop_duplicates()
    if frame.duplicated(['trade_date', 'symbol', 'series']).any():
        raise ValueError('Conflicting identity observations')
    frame = frame.sort_values(['symbol', 'series', 'trade_date'])
    previous = frame.groupby(['symbol', 'series'], dropna=False)['isin'].shift()
    frame['_run'] = frame['isin'].ne(previous).cumsum()
    result = frame.groupby(['symbol', 'series', '_run'], dropna=False).agg(
        isin=('isin', 'first'), valid_from=('trade_date', 'min'), valid_to=('trade_date', 'max')).reset_index()
    result['instrument_id'] = result['isin'].map(instrument_id)
    result['identity_status'] = result.instrument_id.map(lambda value: 'RESOLVED' if value else 'UNRESOLVED')
    result['isin'] = result['isin'].replace('', None)
    return result[columns].sort_values(['symbol', 'series', 'valid_from']).reset_index(drop=True)


def resolve_identity(history, symbol, day, series='EQ'):
    if history.empty:
        return None
    day = pd.Timestamp(day)
    rows = history[(history.symbol == symbol) & (history.series == series)
                   & (history.valid_from <= day) & (history.valid_to >= day)
                   & (history.identity_status == 'RESOLVED')]
    ids = rows.instrument_id.dropna().unique()
    return ids[0] if len(ids) == 1 else None


def attach_identities(prices):
    frame = prices.copy()
    frame['instrument_id'] = frame['isin'].map(instrument_id)
    frame['identity_status'] = frame.instrument_id.map(lambda value: 'RESOLVED' if value else 'UNRESOLVED')
    return frame
