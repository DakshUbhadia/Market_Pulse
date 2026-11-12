"""NSE listed equity snapshot. Unpublished tick sizes stay unknown."""
import pandas as pd

from quant.data.normalization import dates, keys, mapped_csv, numeric, provenance

MAPPING = dict(symbol='SYMBOL', security_name='NAME OF COMPANY', series='SERIES',
               listing_date='DATE OF LISTING', isin='ISIN NUMBER', face_value='FACE VALUE')


def source_url(base='https://nsearchives.nseindia.com'):
    return base.rstrip('/') + '/content/equities/EQUITY_L.csv'


def parse_security_master(content, snapshot_date, url=None):
    frame = mapped_csv(content, MAPPING)
    dates(frame, 'listing_date')
    numeric(frame, ['face_value'])
    if not frame['isin'].str.fullmatch(r'IN[A-Z0-9]{10}').all():
        raise ValueError('Invalid NSE ISIN')
    keys(frame, ['symbol', 'series'])
    frame['snapshot_date'] = pd.Timestamp(snapshot_date)
    frame['instrument_type'] = 'EQUITY'
    frame['listing_status'] = 'LISTED'  # In this NSE list; not proof of active daily trading.
    frame['tick_size'] = float('nan')
    return provenance(frame, content, url or source_url())
