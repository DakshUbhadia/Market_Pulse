"""Official Nifty Indices total-return history; close-only, never synthetic opens."""
import json

import numpy as np
import pandas as pd

SOURCE_URL = 'https://niftyindices.com/Backpage/getTotalReturnIndexString'
SOURCE_PAGE = 'https://niftyindices.com/reports/historical-data'
BENCHMARKS = ('NIFTY 50', 'NIFTY 500')


def parse_tri(content, name, start, end):
    if name not in BENCHMARKS:
        raise ValueError('Unsupported TRI benchmark')
    payload = json.loads(content)
    if isinstance(payload, dict) and 'd' in payload:
        payload = json.loads(payload['d']) if isinstance(payload['d'], str) else payload['d']
    frame = pd.DataFrame(payload)
    required = ['Index Name', 'Date', 'TotalReturnsIndex']
    if frame.empty or not set(required).issubset(frame.columns):
        raise ValueError('Empty or changed official TRI schema')
    if not frame['Index Name'].str.upper().str.strip().eq(name).all():
        raise ValueError('Unexpected TRI identity')
    result = pd.DataFrame(dict(trade_date=pd.to_datetime(frame.Date, format='%d %b %Y'),
        close=pd.to_numeric(frame.TotalReturnsIndex, errors='raise'), index_name=name + ' TRI'))
    if (not result.trade_date.between(pd.Timestamp(start), pd.Timestamp(end)).all()
            or result.trade_date.duplicated().any() or not np.isfinite(result.close).all()
            or result.close.le(0).any()):
        raise ValueError('Invalid TRI observations')
    result['return_basis'] = 'TOTAL_RETURN'
    return result.sort_values('trade_date').reset_index(drop=True)
