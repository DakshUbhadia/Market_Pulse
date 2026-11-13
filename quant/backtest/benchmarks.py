import pandas as pd

from quant.backtest.portfolio import capped_inverse_volatility


def index_returns(index, dates):
    rows = index.set_index('trade_date').reindex(pd.DatetimeIndex(dates))
    if rows[['open', 'close']].isna().any().any() or (rows[['open', 'close']] <= 0).any().any():
        raise ValueError('Incomplete benchmark prices')
    result = rows.close.pct_change(fill_method=None)
    if len(rows):
        result.iloc[0] = rows.close.iloc[0]/rows.open.iloc[0] - 1
    return result


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
