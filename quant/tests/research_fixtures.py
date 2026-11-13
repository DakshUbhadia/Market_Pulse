import numpy as np
import pandas as pd


def market_fixture(stocks=12, days=330, start='2023-01-02'):
    sessions = pd.bdate_range(start, periods=days)
    t = np.arange(days)
    market_return = .0004 + .006*np.sin(t*.21)
    market_close = 100*np.cumprod(1+market_return)
    benchmark = pd.DataFrame(dict(trade_date=sessions, open=np.r_[100, market_close[:-1]], close=market_close))
    rows = []
    for j in range(stocks):
        close = (50+j)*np.cumprod(1 + market_return*(.5+j/stocks) + .004*np.sin(t*.37+j))
        open_ = np.r_[50+j, close[:-1]]*(1+.001*np.cos(t*.31+j))
        rows.append(pd.DataFrame(dict(trade_date=sessions, instrument_id=f'id-{j:03d}',
            symbol=f'STOCK{j:03d}', series='EQ', adjusted_open=open_, adjusted_high=np.maximum(open_,close)*1.01,
            adjusted_low=np.minimum(open_,close)*.99, adjusted_close=close, raw_open=open_, raw_high=np.maximum(open_,close)*1.01,
            raw_low=np.minimum(open_,close)*.99, raw_close=close, close=close, open=open_,
            high=np.maximum(open_,close)*1.01, low=np.minimum(open_,close)*.99,
            volume=1_000_000+j, traded_value=100_000_000+j*10_000_000, adjustment_status='OK',
            source_price_sha256='a'*64, split_factor=1.0, total_return_close=close)))
    return pd.concat(rows, ignore_index=True), benchmark, sessions


def execution_scores(prices):
    frame = prices[['trade_date', 'instrument_id', 'symbol']].rename(columns={'trade_date':'as_of'}).copy()
    frame['raw_score'] = frame.instrument_id.str[-3:].astype(int)
    frame['percentile_score'] = frame.groupby('as_of').raw_score.rank(pct=True)*100
    frame['vol_63'] = .2
    frame['eligible'] = True
    frame['feature_valid'] = True
    frame['mom_252_ex_21'] = frame.raw_score
    return frame
