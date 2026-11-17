"""Monthly signals at close t; fills use only the next exchange-session open.

Fractional split-adjusted research units are supported. Supplying corporate
actions enables gross ex-date cash dividends on prior-close holdings.
Unquoted holdings stop the run rather than silently deleting delisting losses.
"""
from quant.lifecycle.policy import DEFAULT_LIFECYCLE_SCENARIO, resolve_lifecycle_events
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from quant.backtest.portfolio import PortfolioConfig, target_portfolio
from quant.backtest.costs import CostModel
from quant.backtest.execution import executable, affordable_quantity
from quant.universe.eligible import session_index
from quant.backtest.corporate_actions import dividend_events, dividend_credits, DIVIDEND_CONVENTION
from quant.backtest.lifecycle import Lifecycle, simulation_time, share_factor, UnvaluedHolding


@dataclass
class BacktestResult:
    equity_curve: pd.DataFrame
    trades: pd.DataFrame
    holdings: pd.DataFrame
    limitations: list
    skipped_orders: pd.DataFrame
    dividends: pd.DataFrame = field(default_factory=pd.DataFrame)
    lifecycle: pd.DataFrame = field(default_factory=pd.DataFrame)


def monthly_signal_dates(sessions):
    dates = session_index(sessions)
    return {dates[i] for i in range(len(dates)-1) if dates[i].to_period('M') != dates[i+1].to_period('M')}


def run_backtest(prices, scores, sessions, *, start=None, end=None, portfolio=None,
                 cost_model=None, target_builder=None, corporate_actions=None, lifecycle_events=None,
                 lifecycle_scenario=DEFAULT_LIFECYCLE_SCENARIO, lifecycle=None, signal_dates=None):
    # Session order: state/economics, executable holdings, orders, dividends,
    # valuation. Dividend entitlement is captured from the preceding close.
    lifecycle_events = resolve_lifecycle_events(lifecycle, lifecycle_events)
    config, costs = portfolio or PortfolioConfig(), cost_model or CostModel()
    dates = session_index(sessions)
    first = pd.Timestamp(start) if start is not None else dates[0]
    last = pd.Timestamp(end) if end is not None else dates[-1]
    fields = ['trade_date','instrument_id','series','adjusted_open','adjusted_close','adjustment_status','volume']
    fields += [name for name in ('split_factor','raw_close') if name in prices]
    policy = Lifecycle(lifecycle_events, lifecycle_scenario)
    identities = set(scores.instrument_id.unique())
    if lifecycle_events is not None and not lifecycle_events.empty:
        identities.update(lifecycle_events.successor_instrument_id.dropna())
    frame = prices.loc[prices.series.eq('EQ') & prices.instrument_id.isin(identities), fields].copy()
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
    signals = monthly_signal_dates(dates) if signal_dates is None else set(pd.to_datetime(signal_dates))
    cash, positions, basis = config.initial_cash, {}, {}
    equity, trades, holdings, skipped = [], [], [], []
    prior_nav = config.initial_cash
    estimated_costs = False
    events = dividend_events(corporate_actions)
    dividend_records = []
    lifecycle_records, processed, last_bars = [], set(), {}
    offer_entitlements = {}
    for i, day in enumerate(dates):
        if day < first or day > last:
            continue
        today = (frame.iloc[by_day[day]].set_index('instrument_id').to_dict('index') if day in by_day else {})
        signal_day = dates[i-1] if i > 0 else None
        traded_value = 0.0
        cash_income = 0.0
        credits = dividend_credits(events[day], positions.copy(), {**last_bars, **today}, day) if day in events else []
        opening = simulation_time(day, '09:15')
        if lifecycle_scenario == 'FORMAL_EXIT_OFFER_PARTICIPATION':
            # Only shares already held by the offer deadline may participate.
            # Later purchases cannot acquire a retroactive tender entitlement.
            for identity in policy.by_identity:
                for offer in policy.known(identity,opening).to_dict('records'):
                    key = offer['lifecycle_event_id']
                    if (offer['event_type'] in ('EXIT_OFFER','TENDER_OFFER') and offer['optional']
                            and key not in offer_entitlements and pd.notna(offer['offer_end'])
                            and offer['offer_end'] <= day):
                        quantity = positions.get(identity,0.)
                        offer_entitlements[key] = quantity*share_factor(last_bars.get(identity,{})) if quantity else 0.
        for identity in list(positions):
            for event in policy.resolutions(identity, opening, processed):
                quantity = positions[identity]
                factor = share_factor(today.get(identity, last_bars.get(identity, {})))
                raw_quantity = quantity * factor
                kind = event['event_type']
                if kind in ('EXIT_OFFER','TENDER_OFFER'):
                    raw_quantity = min(raw_quantity,offer_entitlements.get(event['lifecycle_event_id'],0.))
                    if raw_quantity <= 0:
                        continue
                    quantity = raw_quantity/factor
                credit, successor_quantity = 0., 0.
                if kind in ('CASH_SETTLEMENT', 'EXIT_OFFER', 'TENDER_OFFER'):
                    amount = event['cash_per_raw_share'] if kind == 'CASH_SETTLEMENT' else event['offer_price']
                    if not np.isfinite(amount) or amount < 0:
                        raise ValueError('Invalid mandatory settlement')
                    credit = raw_quantity * amount
                    cash += credit
                elif kind == 'ZERO_RECOVERY':
                    if event['cash_per_raw_share'] != 0:
                        raise ValueError('Zero recovery requires explicit verified zero economics')
                else:
                    successor = event['successor_instrument_id']
                    ratio = event['conversion_ratio']
                    if not successor or successor == identity or not np.isfinite(ratio) or ratio <= 0:
                        raise ValueError('Invalid mandatory conversion')
                    successor_quantity = raw_quantity * ratio / share_factor(today.get(successor, {}))
                    existing = positions.get(successor, 0.)
                    basis[successor] = (quantity*basis[identity] + existing*basis.get(successor,0)) / (existing+successor_quantity)
                    positions[successor] = existing+successor_quantity
                original_basis = quantity * basis[identity]
                remaining = positions[identity]-quantity
                if remaining <= 1e-10:
                    positions.pop(identity)
                    basis.pop(identity, None)
                else:
                    positions[identity] = remaining
                processed.add(event['lifecycle_event_id'])
                lifecycle_records.append(dict(trade_date=day, instrument_id=identity,
                    event_id=event['lifecycle_event_id'], event_type=kind, raw_quantity=raw_quantity,
                    cash_credit=credit, successor_quantity=successor_quantity,
                    successor_instrument_id=event.get('successor_instrument_id'),
                    transferred_cost_basis=original_basis, scenario=lifecycle_scenario))
        # Dated risk exits run every session, before monthly portfolio orders.
        if lifecycle_scenario == 'KNOWN_EVENT_NEXT_OPEN_EXIT':
            for identity in list(positions):
                status = policy.status(identity, opening - pd.Timedelta(nanoseconds=1))
                if status['entry_allowed']:
                    continue
                bar = today.get(identity)
                if not executable(bar) or not status['trading_allowed']:
                    skipped.append(dict(trade_date=day, signal_date=signal_day, instrument_id=identity,
                        side='SELL',reason='LIFECYCLE_NO_EXECUTABLE_OPEN'))
                    continue
                quantity, price = positions[identity], bar['adjusted_open']
                turnover = quantity*price
                fee = costs.cost(date=day,side='SELL',turnover=turnover)
                cash += turnover-fee['total']
                estimated_costs |= not fee['schedule_verified']
                trades.append(dict(trade_date=day, signal_date=signal_day, instrument_id=identity,side='SELL',
                    quantity=quantity,price=price,turnover=turnover,
                    realized_pnl=quantity*(price-basis[identity])-fee['total'],
                    exit_reason='KNOWN_LIFECYCLE_RISK', **fee))
                traded_value += turnover
                positions.pop(identity)
                basis.pop(identity,None)
        if signal_day in signals and signal_day not in by_signal:
            raise ValueError(f'Missing research rankings at rebalance close {signal_day.date()}')
        if signal_day in signals and signal_day in by_signal:
            selected = scores.iloc[by_signal[signal_day]]
            selected = selected[selected.instrument_id.map(lambda identity: policy.status(identity,
                opening - pd.Timedelta(nanoseconds=1))['entry_allowed'])]
            weights = (target_builder(selected, positions, config) if target_builder
                       else target_portfolio(selected, positions, config))
            if (not np.isfinite(weights).all() or (weights < 0).any()
                    or weights.sum() > 1+1e-10 or (weights > config.max_weight+1e-10).any()):
                raise ValueError('Invalid target portfolio weights')
            target = {identity: prior_nav*weight for identity, weight in weights.items()}
            # Sell before buying. Missing/suspended opens do not generate fills.
            for identity in sorted(set(positions) | set(target)):
                bar = today.get(identity)
                if not executable(bar) or not policy.status(identity, opening)['trading_allowed']:
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
                if not executable(bar) or not policy.status(identity, opening)['trading_allowed']:
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
        dividend_records.extend(credits)
        cash_income = sum(row['cash_credit'] for row in credits)
        cash += cash_income
        nav = cash
        for identity, quantity in list(positions.items()):
            bar = today.get(identity)
            if (not executable(bar) or not policy.status(identity, simulation_time(day,'15:30'))['trading_allowed']
                    or not np.isfinite(bar.get('adjusted_close', np.nan)) or bar['adjusted_close'] <= 0):
                if lifecycle_scenario == 'ZERO_RECOVERY_STRESS':
                    lifecycle_records.append(dict(trade_date=day, instrument_id=identity,
                        event_id=None, event_type='HYPOTHETICAL_ZERO_RECOVERY', cash_credit=0.,
                        written_off_cost_basis=quantity*basis[identity], scenario=lifecycle_scenario))
                    positions.pop(identity)
                    basis.pop(identity)
                    continue
                raise UnvaluedHolding(identity,day)
            value = quantity*bar['adjusted_close']
            nav += value
            holdings.append(dict(trade_date=day, instrument_id=identity, quantity=quantity, value=value))
        last_bars.update(today)
        if cash < -1e-7 or nav < 0 or (nav == 0 and lifecycle_scenario != 'ZERO_RECOVERY_STRESS'):
            raise ValueError('Invalid cash/NAV in simulation')
        equity.append(dict(trade_date=day, nav=nav, cash=cash, daily_return=nav/prior_nav-1 if prior_nav else 0.,
                           turnover=traded_value/prior_nav if prior_nav else 0., holdings_count=len(positions), dividend_cash=cash_income))
        prior_nav = nav
    limitations = [('PRICE_RETURN: dividends excluded consistently; no total-return alpha claim' if corporate_actions is None
                    else 'TOTAL_RETURN: ' + DIVIDEND_CONVENTION + '; actual payment lag and withholding excluded'),
                   'Fractional split-adjusted units; targets capped at rebalance, weights may drift between rebalances']
    limitations.append(f'LIFECYCLE_SCENARIO: {lifecycle_scenario}; optional participation only in explicit offer scenario; '
                       'zero write-offs only in explicit stress scenario; otherwise unresolved valuations block')
    if estimated_costs:
        limitations.append('ESTIMATED_HISTORICAL_COSTS: not eligible for a validated investment conclusion')
    return BacktestResult(pd.DataFrame(equity), pd.DataFrame(trades), pd.DataFrame(holdings), limitations,
        pd.DataFrame(skipped, columns=['trade_date','signal_date','instrument_id','side','reason']),
        pd.DataFrame(dividend_records, columns=['trade_date','event_id','instrument_id','quantity',
            'dividend_per_share','split_factor','cash_credit','convention']), pd.DataFrame(lifecycle_records))
