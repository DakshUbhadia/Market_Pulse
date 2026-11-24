import numpy as np
import pandas as pd

from quant.universe.eligible import panels, session_index
from quant.version import LABEL_CONTRACT_VERSION


def forward_labels(prices, benchmark, sessions, *, horizon=63, signal_keys=None):
    if horizon < 1:
        raise ValueError('Horizon must be positive')
    dates = session_index(sessions)
    market = benchmark.set_index('trade_date').reindex(dates)
    keys = ['as_of', 'instrument_id']
    if signal_keys is not None:
        signal_keys = signal_keys[keys].copy()
        signal_keys['as_of'] = pd.to_datetime(signal_keys.as_of)
        if signal_keys.duplicated(keys).any() or not signal_keys.as_of.isin(dates).all():
            raise ValueError('Label signals require unique identity/session pairs on the exchange calendar')
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
        stock_entry, stock_exit = panel.adjusted_open.shift(-1), panel.adjusted_close.shift(-horizon)
        stock = stock_exit / stock_entry - 1
        m = market.reindex(panel.index)
        benchmark_entry, benchmark_exit = m.open.shift(-1), m.close.shift(-horizon)
        bench = benchmark_exit / benchmark_entry - 1
        returns = panel.adjusted_close.pct_change(fill_method=None)
        first = panel.adjusted_close.shift(-1)/panel.adjusted_open.shift(-1)-1
        sums = returns.rolling(horizon).sum().shift(-horizon) - returns.shift(-1) + first
        squares = returns.pow(2).rolling(horizon).sum().shift(-horizon) - returns.shift(-1).pow(2) + first.pow(2)
        future_vol = ((squares-sums.pow(2)/horizon)/(horizon-1)).clip(lower=0).pow(.5)*np.sqrt(252) if horizon > 1 else np.nan
        stock_entry_valid = np.isfinite(stock_entry) & stock_entry.gt(0) & panel.volume.shift(-1).gt(0)
        stock_exit_valid = np.isfinite(stock_exit) & stock_exit.gt(0) & panel.volume.shift(-horizon).gt(0)
        benchmark_valid = np.isfinite(benchmark_entry) & benchmark_entry.gt(0) & np.isfinite(benchmark_exit) & benchmark_exit.gt(0)
        status = np.select([exit_.isna(), ~stock_entry_valid, ~stock_exit_valid, ~benchmark_valid,
            ~np.isfinite(stock) | ~np.isfinite(bench)],
            ['IMMATURE', 'MISSING_OR_INVALID_ENTRY', 'MISSING_OR_INVALID_EXIT', 'INVALID_BENCHMARK', 'INVALID_RETURN'],
            default='MATURE')
        available = status == 'MATURE'
        out = pd.DataFrame(dict(instrument_id=panel.instrument_id, entry_date=entry, exit_date=exit_,
            entry_price=stock_entry, exit_price=stock_exit,
            benchmark_entry_price=benchmark_entry, benchmark_exit_price=benchmark_exit,
            stock_return_63=stock.where(available), benchmark_return_63=bench.where(available),
            excess_return_63=(stock - bench).where(available),
            future_volatility_63=pd.Series(future_vol, index=panel.index).where(available),
            label_available=available, maturity_status=status), index=panel.index)
        out.index.name = 'as_of'
        observed = panel.observed.fillna(False)
        if wanted is not None:
            observed &= panel.index.isin(wanted[identity])
        rows.append(out.loc[observed].reset_index())
    result = pd.concat(rows, ignore_index=True) if rows else pd.DataFrame(columns=keys+[
        'entry_date', 'exit_date', 'entry_price', 'exit_price', 'benchmark_entry_price', 'benchmark_exit_price',
        'stock_return_63', 'benchmark_return_63', 'excess_return_63', 'future_volatility_63', 'label_available',
        'maturity_status'])
    if not rows:
        result['as_of'] = pd.Series(dtype='datetime64[ns]')
    if signal_keys is not None and len(signal_keys):
        population = signal_keys.merge(result[keys], on=keys, how='left', validate='one_to_one', indicator=True)
        missing = population.loc[population['_merge'].eq('left_only'), keys].copy()
        if not missing.empty:
            calendar = pd.Series(dates, index=dates)
            missing['entry_date'] = missing.as_of.map(calendar.shift(-1))
            missing['exit_date'] = missing.as_of.map(calendar.shift(-horizon))
            missing['maturity_status'] = 'MISSING_SIGNAL_OBSERVATION'
            missing['label_available'] = False
            result = pd.concat([result, missing.reindex(columns=result.columns)], ignore_index=True)
    result['signal_at'], result['entry_at'], result['label_end_at'] = result.as_of, result.entry_date, result.exit_date
    # The input calendar resolves session dates. It does not establish intraday availability.
    result['label_available_at'] = result.exit_date.where(result.label_available.eq(True))
    result['benchmark_basis'] = 'PRICE'
    result['timestamp_precision'] = 'EXCHANGE_SESSION_DATE'
    result['label_contract_version'] = LABEL_CONTRACT_VERSION
    return result
