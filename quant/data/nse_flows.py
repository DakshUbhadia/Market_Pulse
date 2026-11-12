"""Provisional FII/DII cash activity; a snapshot source, not historical daily OHLC."""
import pandas as pd

from quant.data.normalization import dates, keys, numeric, records

PATH = '/api/fiidiiTradeReact'


def parse_flows(payload, raw):
    rows = []
    for record in records(payload):
        category = str(record.get('category', '')).upper()
        participant = 'FII' if 'FII' in category or 'FPI' in category else 'DII' if 'DII' in category else None
        if participant is None or not record.get('date'):
            raise ValueError('FII/DII schema changed')
        rows.append(dict(trade_date=record['date'], participant_type=participant,
                         buy_value=str(record.get('buyValue', '')).replace(',', ''),
                         sell_value=str(record.get('sellValue', '')).replace(',', ''),
                         net_value=str(record.get('netValue', '')).replace(',', ''),
                         status='PROVISIONAL', source='NSE', source_url=raw.source_url,
                         source_sha256=raw.sha256, fetched_at=raw.fetched_at, unit='INR_CRORE'))
    frame = pd.DataFrame(rows)
    if frame.empty:
        raise ValueError('No FII/DII snapshot')
    dates(frame, 'trade_date')
    numeric(frame, ['buy_value', 'sell_value'])
    numeric(frame, ['net_value'], nonnegative=False)
    if ((frame.buy_value - frame.sell_value - frame.net_value).abs() > .02).any():
        raise ValueError('FII/DII net value does not reconcile')
    keys(frame, ['trade_date', 'participant_type'])
    return frame
