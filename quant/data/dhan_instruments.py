"""Current identity snapshot; never a historical universe membership filter."""
from datetime import datetime, timezone
from io import BytesIO
from uuid import NAMESPACE_URL, uuid5

import pandas as pd

from quant.data.http import Downloader, sha256

MASTER_URL = 'https://images.dhan.co/api-data/api-scrip-master-detailed.csv'


def parse_instruments(content: bytes) -> pd.DataFrame:
    raw = pd.read_csv(BytesIO(content), dtype=str, keep_default_na=False)
    raw.columns = raw.columns.str.strip()
    required = {'EXCH_ID', 'SEGMENT', 'SECURITY_ID', 'ISIN', 'SYMBOL_NAME', 'UNDERLYING_SYMBOL', 'SERIES', 'INSTRUMENT'}
    if not required.issubset(raw.columns):
        raise ValueError(f'Missing Dhan columns: {sorted(required - set(raw.columns))}')
    raw = raw.map(lambda value: value.strip() if isinstance(value, str) else value)
    equities = raw[(raw.EXCH_ID.isin(['NSE', 'BSE'])) & (raw.SEGMENT == 'E')
                   & (raw.INSTRUMENT == 'EQUITY') & (raw.ISIN != '')]
    nse = equities[(equities.EXCH_ID == 'NSE') & (equities.SERIES == 'EQ')].copy()
    if (nse.empty or nse.duplicated(['ISIN']).any() or nse.duplicated(['UNDERLYING_SYMBOL']).any()
            or (nse.UNDERLYING_SYMBOL == '').any()):
        raise ValueError('Empty or ambiguous NSE EQ instrument mapping')
    bse = equities[equities.EXCH_ID == 'BSE']
    # An ambiguous cross-listing stays unmapped rather than choosing an arbitrary record.
    bse = bse[~bse.duplicated('ISIN', keep=False)].set_index('ISIN')
    result = pd.DataFrame({
        'instrument_id': nse.ISIN.map(lambda isin: str(uuid5(NAMESPACE_URL, 'isin:' + isin))),
        'isin': nse.ISIN, 'nse_symbol': nse.UNDERLYING_SYMBOL,
        'company_name': nse.SYMBOL_NAME, 'series': nse.SERIES,
        'dhan_security_id': nse.SECURITY_ID,
        'bse_scrip_code': nse.ISIN.map(bse.SECURITY_ID),
        'bse_symbol': nse.ISIN.map(bse.UNDERLYING_SYMBOL),
        'yahoo_nse_symbol': nse.UNDERLYING_SYMBOL + '.NS',
    })
    result['yahoo_bse_symbol'] = result.bse_symbol + '.BO'
    result['source_file'] = MASTER_URL
    result['source_hash'] = sha256(content)
    return result.reset_index(drop=True)


def download_instruments(downloader: Downloader) -> pd.DataFrame:
    now = datetime.now(timezone.utc)
    path = downloader.config.data_dir / 'raw' / 'dhan' / f'{now:%Y-%m-%d}-instruments.csv'
    frame = downloader.fetch_parsed(MASTER_URL, path, parse_instruments)
    # Download timestamp is retained in the raw sidecar; snapshot date is not listing date.
    frame['snapshot_date'] = now.date().isoformat()
    return frame
