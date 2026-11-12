"""Backward adjustments on a copy; raw prices are never changed.

Dividends are reinvested at the ex-date close. Complex actions and
unresolved identities produce null research prices, rather than false returns.
"""
import numpy as np
import pandas as pd

from quant.data.security_history import attach_identities


def _adjust_group(prices, actions):
    frame = attach_identities(prices) if 'instrument_id' not in prices else prices.copy()
    frame = frame.sort_values(['instrument_id', 'symbol', 'series', 'trade_date']).reset_index(drop=True)
    frame['trade_date'] = pd.to_datetime(frame.trade_date).dt.normalize()
    frame['raw_close'] = frame.close.astype(float)
    if not np.isfinite(frame.raw_close).all() or (frame.raw_close <= 0).any():
        raise ValueError('Invalid raw close')
    frame['split_adjustment_factor'] = 1.0
    frame['total_return_adjustment_factor'] = 1.0
    frame['adjustment_status'] = 'OK'
    frame.loc[frame.instrument_id.isna(), 'adjustment_status'] = 'UNRESOLVED_IDENTITY'
    frame.loc[frame.series == 'T0', 'adjustment_status'] = 'NON_STANDARD_CLOSE'
    frame.loc[frame.series == '', 'adjustment_status'] = 'MISSING_SERIES'
    if not actions.empty:
        actions = actions.drop_duplicates('event_id').copy()
        actions['ex_date'] = pd.to_datetime(actions.ex_date).dt.normalize()
        for action in actions.sort_values('ex_date').itertuples():
            if action.parse_status == 'NON_ADJUSTING':
                continue
            # ISIN permits a split across symbol changes. A missing identity never links companies.
            selected = (frame.instrument_id == action.instrument_id) if pd.notna(action.instrument_id) else (frame.symbol == action.symbol)
            if not selected.any() or action.ex_date > frame.loc[selected, 'trade_date'].max():
                continue
            duplicate = actions[(actions.symbol == action.symbol) & (actions.ex_date == action.ex_date)
                                & (actions.action_type == action.action_type)]
            if (action.parse_status != 'PARSED' or action.action_type not in ('SPLIT', 'BONUS', 'DIVIDEND')
                    or len(duplicate) != 1 or pd.isna(action.instrument_id)):
                frame.loc[selected, 'adjustment_status'] = 'NEEDS_REVIEW'
                continue
            before = selected & (frame.trade_date < action.ex_date)
            if not before.any():
                continue
            multiplier = 1.0
            if action.action_type in ('SPLIT', 'BONUS'):
                n, d = action.ratio_numerator, action.ratio_denominator
                if pd.isna(n) or pd.isna(d) or not np.isfinite([n, d]).all() or min(n, d) <= 0:
                    frame.loc[selected, 'adjustment_status'] = 'NEEDS_REVIEW'
                    continue
                multiplier = d / n if action.action_type == 'SPLIT' else d / (n + d)
                frame.loc[before, 'split_adjustment_factor'] *= multiplier
            else:
                # A simultaneous split/dividend requires explicit share-basis reconciliation.
                simultaneous = actions[(actions.symbol == action.symbol) & (actions.ex_date == action.ex_date)
                                       & actions.action_type.isin(['SPLIT', 'BONUS'])]
                prior = frame.loc[before].sort_values('trade_date').raw_close.iloc[-1]
                cash = action.cash_amount
                ex_bars = frame.loc[selected & (frame.trade_date == action.ex_date)]
                if (not simultaneous.empty or len(ex_bars) != 1 or pd.isna(cash)
                        or not np.isfinite(cash) or not 0 <= cash < prior):
                    frame.loc[selected, 'adjustment_status'] = 'NEEDS_REVIEW'
                    continue
                ex_close = ex_bars.raw_close.iloc[0]
                multiplier = ex_close / (ex_close + cash)
            frame.loc[before, 'total_return_adjustment_factor'] *= multiplier
    frame['adjusted_close'] = frame.raw_close * frame.split_adjustment_factor
    frame['total_return_close'] = frame.raw_close * frame.total_return_adjustment_factor
    excluded = frame.adjustment_status != 'OK'
    frame.loc[excluded, ['adjusted_close', 'total_return_close']] = np.nan
    return frame


def adjust_prices(prices, actions):
    """Partition by identity before applying events, avoiding a corpus-wide event scan."""
    frame = attach_identities(prices) if 'instrument_id' not in prices else prices.copy()
    if frame.empty:
        raise ValueError('No prices to adjust')
    frame['_identity'] = frame.instrument_id.fillna('UNRESOLVED:' + frame.symbol)
    by_id, by_symbol = {}, {}
    if not actions.empty:
        by_id = {key: group for key, group in actions.dropna(subset=['instrument_id']).groupby('instrument_id')}
        by_symbol = {key: group for key, group in actions[actions.instrument_id.isna()].groupby('symbol')}
    groups = []
    for (identity, series), bars in frame.groupby(['_identity', 'series'], sort=False):
        candidates = [by_id[identity]] if identity in by_id else []
        candidates.extend(by_symbol[symbol] for symbol in bars.symbol.unique() if symbol in by_symbol)
        events = pd.concat(candidates, ignore_index=True) if candidates else actions.iloc[:0]
        groups.append(_adjust_group(bars.drop(columns='_identity'), events))
    return pd.concat(groups, ignore_index=True)
