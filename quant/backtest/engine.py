"""Monthly signals at close t; fills use only the next exchange-session open.

Fractional split-adjusted research units are supported. This V1 simulator uses
price returns on both stocks and benchmark indices; cash dividends are excluded.
Unquoted holdings stop the run rather than silently deleting delisting losses.
"""
from dataclasses import dataclass

import numpy as np
import pandas as pd

from quant.backtest.portfolio import PortfolioConfig, target_portfolio
from quant.backtest.costs import CostModel
from quant.backtest.execution import executable, affordable_quantity
from quant.universe.eligible import session_index


@dataclass
class BacktestResult:
    equity_curve: pd.DataFrame
    trades: pd.DataFrame
    holdings: pd.DataFrame
    limitations: list
    skipped_orders: pd.DataFrame


def monthly_signal_dates(sessions):
    dates = session_index(sessions)
    return {dates[i] for i in range(len(dates)-1) if dates[i].to_period('M') != dates[i+1].to_period('M')}


def run_backtest(prices, scores, sessions, *, start=None, end=None, portfolio=None,
                 cost_model=None, target_builder=None):
    config, costs = portfolio or PortfolioConfig(), cost_model or CostModel()
    dates = session_index(sessions)
    first = pd.Timestamp(start) if start is not None else dates[0]
    last = pd.Timestamp(end) if end is not None else dates[-1]
    fields = ['trade_date','instrument_id','series','adjusted_open','adjusted_close','adjustment_status','volume']
    frame = prices.loc[prices.series.eq('EQ') & prices.instrument_id.isin(scores.instrument_id.unique()), fields].copy()
    frame['trade_date'] = pd.to_datetime(frame.trade_date)
    frame = frame.dropna(subset=['instrument_id'])
    if frame.duplicated(['trade_date', 'instrument_id']).any():
        raise ValueError('Ambiguous execution bars')
    if scores.duplicated(['as_of', 'instrument_id']).any():
        raise ValueError('Duplicate score keys')
    # Store integer locations, not millions of Python dictionaries. Materialize
    # only today's bars and each monthly cross section during a simulation.
    by_day = frame.groupby('trade_date', sort=False).indices
    by_signal = {pd.Timestamp(day): locations for day, locations in scores.groupby('as_of', sort=False).indices.items()}
    signals = monthly_signal_dates(dates)
    cash, positions, basis = config.initial_cash, {}, {}
    equity, trades, holdings, skipped = [], [], [], []
    prior_nav = config.initial_cash
    estimated_costs = False
    for i, day in enumerate(dates):
        if day < first or day > last:
            continue
        today = (frame.iloc[by_day[day]].set_index('instrument_id').to_dict('index') if day in by_day else {})
        signal_day = dates[i-1] if i > 0 else None
        traded_value = 0.0
        if signal_day in signals and signal_day not in by_signal:
            raise ValueError(f'Missing research rankings at rebalance close {signal_day.date()}')
        if signal_day in signals and signal_day in by_signal:
            selected = scores.iloc[by_signal[signal_day]]
            weights = (target_builder(selected, positions, config) if target_builder
                       else target_portfolio(selected, positions, config))
            if (not np.isfinite(weights).all() or (weights < 0).any()
                    or weights.sum() > 1+1e-10 or (weights > config.max_weight+1e-10).any()):
                raise ValueError('Invalid target portfolio weights')
            target = {identity: prior_nav*weight for identity, weight in weights.items()}
            # Sell before buying. Missing/suspended opens do not generate fills.
            for identity in sorted(set(positions) | set(target)):
                bar = today.get(identity)
                if not executable(bar):
                    skipped.append(dict(trade_date=day, signal_date=signal_day, instrument_id=identity,
                        side='REBALANCE', reason='NO_EXECUTABLE_NEXT_OPEN'))
                    continue
                price = bar['adjusted_open']
                quantity = max(0.0, positions.get(identity, 0) - target.get(identity, 0)/price)
                if quantity <= 1e-10:
                    continue
                turnover = quantity*price
                fee = costs.cost(date=day, side='SELL', turnover=turnover)
                cost_basis = basis.get(identity, price)
                realized_pnl = quantity*(price-cost_basis) - fee['total']
                cash += turnover-fee['total']
                positions[identity] -= quantity
                estimated_costs |= not fee['schedule_verified']
                trades.append(dict(trade_date=day, signal_date=signal_day, instrument_id=identity, side='SELL',
                    quantity=quantity, price=price, turnover=turnover, realized_pnl=realized_pnl, **fee))
                traded_value += turnover
                if positions[identity] < 1e-10:
                    positions.pop(identity)
                    basis.pop(identity, None)
            for identity, amount in target.items():
                bar = today.get(identity)
                if not executable(bar):
                    continue
                price = bar['adjusted_open']
                desired = max(0, amount/price - positions.get(identity, 0))
                quantity = affordable_quantity(cash, price, desired, costs, day) if desired > 0 else 0
                if quantity*price < .01:
                    continue
                turnover = quantity*price
                fee = costs.cost(date=day, side='BUY', turnover=turnover)
                old = positions.get(identity, 0)
                basis[identity] = (old*basis.get(identity, 0) + turnover + fee['total'])/(old+quantity)
                positions[identity] = old+quantity
                cash -= turnover+fee['total']
                estimated_costs |= not fee['schedule_verified']
                trades.append(dict(trade_date=day, signal_date=signal_day, instrument_id=identity, side='BUY',
                    quantity=quantity, price=price, turnover=turnover, realized_pnl=np.nan, **fee))
                traded_value += turnover
        nav = cash
        for identity, quantity in positions.items():
            bar = today.get(identity)
            if bar is None or not np.isfinite(bar.get('adjusted_close', np.nan)) or bar['adjusted_close'] <= 0:
                raise ValueError(f'Unvalued holding {identity} on {day.date()}; verified delisting/settlement evidence required')
            value = quantity*bar['adjusted_close']
            nav += value
            holdings.append(dict(trade_date=day, instrument_id=identity, quantity=quantity, value=value))
        if cash < -1e-7 or nav <= 0:
            raise ValueError('Invalid cash/NAV in simulation')
        equity.append(dict(trade_date=day, nav=nav, cash=cash, daily_return=nav/prior_nav-1,
                           turnover=traded_value/prior_nav, holdings_count=len(positions)))
        prior_nav = nav
    limitations = ['PRICE_RETURN: dividends excluded consistently; no total-return alpha claim',
                   'Fractional split-adjusted units; targets capped at rebalance, weights may drift between rebalances']
    if estimated_costs:
        limitations.append('ESTIMATED_HISTORICAL_COSTS: not eligible for a validated investment conclusion')
    return BacktestResult(pd.DataFrame(equity), pd.DataFrame(trades), pd.DataFrame(holdings), limitations,
        pd.DataFrame(skipped, columns=['trade_date','signal_date','instrument_id','side','reason']))
