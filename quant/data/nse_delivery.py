"""NSE full security-wise delivery report; turnover is normalized to rupees."""
from quant.data.normalization import dates, keys, mapped_csv, numeric, provenance

MAPPING = dict(trade_date='DATE1', symbol='SYMBOL', series='SERIES', volume='TTL_TRD_QNTY',
               traded_value='TURNOVER_LACS', number_of_trades='NO_OF_TRADES',
               deliverable_quantity='DELIV_QTY', deliverable_percent='DELIV_PER')


def source_url(day, base='https://nsearchives.nseindia.com'):
    return f'{base.rstrip("/")}/products/content/sec_bhavdata_full_{day:%d%m%Y}.csv'


def parse_delivery(content, day, url=None):
    frame = mapped_csv(content, MAPPING)
    dates(frame, 'trade_date', expected=day)
    numeric(frame, list(MAPPING)[3:], nullable=('deliverable_quantity', 'deliverable_percent'))
    for name in ('volume', 'number_of_trades', 'deliverable_quantity'):
        if (frame[name].dropna() % 1 != 0).any():
            raise ValueError(f'Fractional {name}')
        frame[name] = frame[name].astype('Int64')
    if (frame.deliverable_percent.dropna() > 100).any() or (frame.deliverable_quantity > frame.volume).any():
        raise ValueError('Invalid delivery quantity or percentage')
    frame['traded_value'] *= 100_000
    keys(frame, ['trade_date', 'symbol', 'series'])
    return provenance(frame, content, url or source_url(day))
