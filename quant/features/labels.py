import numpy as np
import pandas as pd

from quant.universe.eligible import panels, session_index


def forward_labels(prices, benchmark, sessions, *, horizon=63, signal_keys=None):
    if horizon < 1:
        raise ValueError('Horizon must be positive')
    dates = session_index(sessions)
    market = benchmark.set_index('trade_date').reindex(dates)
    wanted = ({identity: pd.DatetimeIndex(group.as_of) for identity, group in signal_keys.groupby('instrument_id')}
              if signal_keys is not None else None)
    rows = []
    for panel in panels(prices, dates):
        identity = panel.instrument_id.iloc[0]
        if wanted is not None and identity not in wanted:
            continue
        # Reindex to the complete evaluation calendar, including unavailable future exits.
        panel = panel.reindex(dates[dates >= panel.index.min()])
        entry = pd.Series(panel.index, index=panel.index).shift(-1)
        exit_ = pd.Series(panel.index, index=panel.index).shift(-horizon)
        stock = panel.adjusted_close.shift(-horizon) / panel.adjusted_open.shift(-1) - 1
        m = market.reindex(panel.index)
        bench = m.close.shift(-horizon) / m.open.shift(-1) - 1
        returns = panel.adjusted_close.pct_change(fill_method=None)
        first = panel.adjusted_close.shift(-1)/panel.adjusted_open.shift(-1)-1
        sums = returns.rolling(horizon).sum().shift(-horizon) - returns.shift(-1) + first
        squares = returns.pow(2).rolling(horizon).sum().shift(-horizon) - returns.shift(-1).pow(2) + first.pow(2)
        future_vol = ((squares-sums.pow(2)/horizon)/(horizon-1)).clip(lower=0).pow(.5)*np.sqrt(252) if horizon > 1 else np.nan
        available = (np.isfinite(stock) & np.isfinite(bench) & panel.adjusted_open.shift(-1).gt(0)
                     & panel.volume.shift(-1).gt(0) & panel.volume.shift(-horizon).gt(0))
        out = pd.DataFrame(dict(instrument_id=panel.instrument_id, entry_date=entry, exit_date=exit_,
            stock_return_63=stock.where(available), benchmark_return_63=bench.where(available),
            excess_return_63=(stock - bench).where(available), future_volatility_63=future_vol,
            label_available=available), index=panel.index)
        out.index.name = 'as_of'
        observed = panel.observed.fillna(False)
        if wanted is not None:
            observed &= panel.index.isin(wanted[identity])
        rows.append(out.loc[observed].reset_index())
    return pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()
