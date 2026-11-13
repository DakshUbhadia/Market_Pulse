import numpy as np
import pandas as pd

from quant.universe.config import UniverseConfig


def session_index(sessions):
    values = pd.DatetimeIndex(pd.to_datetime(sessions)).normalize()
    if values.has_duplicates or not values.is_monotonic_increasing:
        raise ValueError('Sessions must be sorted and unique')
    return values


def panels(prices, sessions):
    """Reindex before all lags. Prices are never forward-filled across missing sessions."""
    calendar = session_index(sessions)
    frame = prices.copy()
    frame['trade_date'] = pd.to_datetime(frame.trade_date).dt.normalize()
    if not frame.trade_date.isin(calendar).all():
        raise ValueError('Prices contain dates outside the supplied exchange calendar')
    frame['_key'] = frame.instrument_id.astype(object).fillna('UNRESOLVED:' + frame.symbol.astype(str))
    for (identity, series), group in frame.groupby(['_key', 'series'], dropna=False, sort=False, observed=True):
        if group.trade_date.duplicated().any():
            raise ValueError('Ambiguous identity/series/session prices')
        group = group.sort_values('trade_date').set_index('trade_date')
        dates = calendar[(calendar >= group.index.min()) & (calendar <= group.index.max())]
        panel = group.reindex(dates)
        panel.index.name = 'as_of'
        panel['observed'] = panel.symbol.notna()
        panel['symbol'] = panel.symbol.ffill()  # Metadata only; retain the symbol known on that date.
        panel['instrument_id'] = group.instrument_id.iloc[0]
        panel['series'] = series
        panel['history_sessions'] = np.arange(1, len(panel) + 1)
        yield panel


def eligibility(panel, config=None):
    config = config or UniverseConfig()
    result = panel[['instrument_id', 'symbol', 'series', 'history_sessions']].copy()
    present = panel.observed & panel.volume.gt(0)
    result['trading_presence_252'] = present.rolling(252, min_periods=1).sum() / 252
    result['adv60'] = panel.traded_value.rolling(60, min_periods=57).median()
    reason = pd.Series('', index=panel.index)
    tests = [
        (panel.series != 'EQ', 'NON_EQ_SERIES'),
        (panel.instrument_id.isna(), 'IDENTITY_UNRESOLVED'),
        (panel.adjustment_status.ne('OK') & panel.observed, 'CORPORATE_ACTION_UNRESOLVED'),
        (panel.history_sessions < config.min_history_sessions, 'INSUFFICIENT_HISTORY'),
        (result.trading_presence_252 < config.min_trading_presence, 'INSUFFICIENT_TRADING_PRESENCE'),
        (result.adv60.isna() | (result.adv60 < config.min_adv60), 'LOW_LIQUIDITY'),
        (~panel.observed | ~panel.volume.gt(0), 'NO_CURRENT_TRADING'),
        (panel.raw_close.lt(config.min_price), 'LOW_PRICE'),
    ]
    for failed, label in tests:
        reason.loc[failed & reason.eq('')] = label
    result['exclusion_reason'] = reason
    result['eligible'] = reason.eq('')
    return result


def build_eligible_universe(prices, sessions, *, as_of=None, config=None):
    if as_of is not None:
        prices = prices[pd.to_datetime(prices.trade_date) <= pd.Timestamp(as_of)]
        sessions = session_index(sessions)[session_index(sessions) <= pd.Timestamp(as_of)]
    rows = [eligibility(panel, config).loc[panel.observed].reset_index() for panel in panels(prices, sessions)]
    if not rows:
        return pd.DataFrame()
    result = pd.concat(rows, ignore_index=True)
    # An absent/delisted security is never included by carrying an old row forward.
    return result[result.as_of.eq(pd.Timestamp(as_of))] if as_of is not None else result
