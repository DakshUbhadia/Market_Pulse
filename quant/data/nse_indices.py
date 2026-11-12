"""All rows from NSE's daily index archive, including sector benchmarks."""
from quant.data.normalization import dates, keys, mapped_csv, numeric, provenance

REQUIRED_INDICES = {'NIFTY 50', 'NIFTY 500', 'NIFTY BANK', 'NIFTY FINANCIAL SERVICES',
                    'NIFTY IT', 'NIFTY AUTO', 'NIFTY FMCG', 'NIFTY PHARMA', 'NIFTY METAL', 'NIFTY REALTY'}
MAPPING = dict(trade_date='Index Date', index_name='Index Name', open='Open Index Value',
               high='High Index Value', low='Low Index Value', close='Closing Index Value',
               shares_traded='Volume', turnover='Turnover (Rs. Cr.)')


def source_url(day, base='https://nsearchives.nseindia.com'):
    return f'{base.rstrip("/")}/content/indices/ind_close_all_{day:%d%m%Y}.csv'


def parse_indices(content, day, url=None):
    frame = mapped_csv(content, MAPPING)
    dates(frame, 'trade_date', expected=day)
    frame['index_name'] = frame.index_name.str.upper()
    numeric(frame, ['open', 'high', 'low', 'close', 'shares_traded', 'turnover'],
            nullable=('open', 'high', 'low', 'shares_traded', 'turnover'))
    if (frame.close <= 0).any():
        raise ValueError('Invalid index close')
    bars = frame.dropna(subset=['open', 'high', 'low'])
    invalid = ((bars.high < bars[['open', 'close', 'low']].max(axis=1))
               | (bars.low > bars[['open', 'close', 'high']].min(axis=1)))
    frame['data_quality'] = 'OK'
    frame.loc[bars.index[invalid], 'data_quality'] = 'INVALID_OHLC'
    frame.loc[frame[['open', 'high', 'low']].isna().any(axis=1), 'data_quality'] = 'CLOSE_ONLY'
    if (invalid & bars.index_name.isin(REQUIRED_INDICES | {'INDIA VIX', 'NIFTY INDIA VIX'})).any():
        raise ValueError('Invalid required index OHLC')
    frame['turnover'] *= 10_000_000
    keys(frame, ['trade_date', 'index_name'])
    return provenance(frame, content, url or source_url(day))
