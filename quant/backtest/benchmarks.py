import pandas as pd
import numpy as np

from quant.backtest.portfolio import capped_inverse_volatility


def index_returns(index, dates):
    rows = index.set_index('trade_date').reindex(pd.DatetimeIndex(dates))
    if rows[['open', 'close']].isna().any().any() or (rows[['open', 'close']] <= 0).any().any():
        raise ValueError('Incomplete benchmark prices')
    result = rows.close.pct_change(fill_method=None)
    if len(rows):
        result.iloc[0] = rows.close.iloc[0]/rows.open.iloc[0] - 1
    return result


def total_return_index_returns(index, dates, sessions=None):
    """Close-to-close TRI; requires the prior session, never invents TRI opens."""
    frame = index.copy()
    frame['trade_date'] = pd.to_datetime(frame.trade_date)
    if frame.trade_date.duplicated().any():
        raise ValueError('Duplicate TRI benchmark sessions')
    close = frame.set_index('trade_date').sort_index().close
    close = close.where(np.isfinite(close) & close.gt(0))
    requested = pd.DatetimeIndex(dates)
    # Validate the previous observation and every requested session explicitly.
    preceding = close.index[close.index < requested[0]] if len(requested) else []
    if sessions is not None and len(requested):
        calendar = pd.DatetimeIndex(sessions)
        preceding = calendar[calendar < requested[0]][-1:]
    if not len(preceding) or close.reindex(requested.union(pd.DatetimeIndex([preceding[-1]]))).isna().any():
        raise ValueError('Incomplete TRI history or missing prior close')
    aligned = close.reindex(pd.DatetimeIndex([preceding[-1]]).append(requested))
    return aligned.pct_change(fill_method=None).reindex(requested)


def baseline_target(name):
    if name not in ('liquid_equal_weight', 'momentum_12_1_top25', 'inverse_volatility'):
        raise ValueError('Unknown baseline')
    def target(rows, current, config):
        rows = rows[rows.eligible].copy().set_index('instrument_id')
        if name == 'momentum_12_1_top25':
            rows = rows.dropna(subset=['mom_252_ex_21']).sort_values('mom_252_ex_21', ascending=False).head(25)
        if rows.empty:
            return pd.Series(dtype=float)
        if name == 'inverse_volatility':
            return capped_inverse_volatility(rows.loc[rows.vol_63 > 0, 'vol_63'].dropna(), config.max_weight)
        weight = min(config.max_weight, 1/len(rows))
        return pd.Series(weight, index=rows.index)
    return target
