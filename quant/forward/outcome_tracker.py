"""Matured next-open outcomes reuse lifecycle, dividend and cost accounting."""
from pathlib import Path

import numpy as np
import pandas as pd

from quant.backtest.engine import run_backtest
from quant.backtest.portfolio import PortfolioConfig
from quant.backtest.execution import executable
from quant.forward.signal_store import append_record, read_signals, content_hash
from quant.universe.eligible import session_index


def track_outcomes(root, prices, benchmark, tri, sessions, *, as_of, cost_model,
                   corporate_actions, lifecycle, lifecycle_scenario, horizons=(21,63)):
    _, signals = read_signals(root)
    dates = session_index(sessions)
    reports = dict(written=0, pending=0, blocked=[])
    market = benchmark.set_index('trade_date')
    total_market = tri.set_index('trade_date')
    # Avoid rescanning the complete historical market for every matured row.
    # Each engine call needs only this security, successor lineage and horizon.
    if signals.empty:
        return reports
    observed = prices[pd.to_datetime(prices.trade_date).between(signals.as_of.min(),pd.Timestamp(as_of))]
    by_identity = observed.groupby('instrument_id',observed=True).indices
    successors = {}
    if lifecycle is not None and not lifecycle.empty:
        for identity, group in lifecycle.groupby('instrument_id'):
            successors[identity] = set(group.successor_instrument_id.dropna())
    for signal in signals.to_dict('records'):
        location = dates.get_indexer([signal['as_of']])[0]
        if location < 0:
            raise ValueError('Frozen signal date missing from exchange calendar')
        for horizon in horizons:
            if horizon not in (21,63):
                raise ValueError('Only predeclared 21/63-session outcomes are supported')
            target = Path(root)/'outcomes'/signal['signal_id']/f'{horizon}.json'
            if target.exists():
                continue
            if location+horizon >= len(dates) or dates[location+horizon] > pd.Timestamp(as_of):
                reports['pending'] += 1
                continue
            entry, exit_ = dates[location+1], dates[location+horizon]
            try:
                b = market.reindex([entry,exit_])
                t = total_market.reindex([signal['as_of'],exit_])
                if (not np.isfinite([b.open.iloc[0],b.close.iloc[1],t.close.iloc[0],t.close.iloc[1]]).all()
                        or min(b.open.iloc[0],b.close.iloc[1],t.close.iloc[0],t.close.iloc[1]) <= 0):
                    raise ValueError('Missing price/TRI benchmark endpoints')
                score = pd.DataFrame([dict(signal, raw_score=signal['score'])])
                identities, pending_ids = {signal['instrument_id']}, [signal['instrument_id']]
                while pending_ids:
                    identity = pending_ids.pop()
                    for successor in successors.get(identity, ()):
                        if successor not in identities:
                            identities.add(successor)
                            pending_ids.append(successor)
                locations = [i for identity in identities for i in by_identity.get(identity, ())]
                asset_prices = observed.iloc[locations]
                window_dates = dates[location:location+horizon+1]
                asset_prices = asset_prices[asset_prices.trade_date.between(window_dates[0],exit_)]
                asset_events = lifecycle[lifecycle.instrument_id.isin(identities)] if lifecycle is not None and not lifecycle.empty else lifecycle
                result = run_backtest(asset_prices,score,window_dates,start=signal['as_of'],end=exit_,
                    signal_dates=[signal['as_of']], portfolio=PortfolioConfig(holdings=1,max_weight=1,
                        entry_percentile=0,exit_percentile=0), cost_model=cost_model,
                    corporate_actions=corporate_actions,lifecycle=asset_events,lifecycle_scenario=lifecycle_scenario)
                if result.trades.empty or not result.trades.side.eq('BUY').any():
                    raise ValueError('No executable next-open entry; no hypothetical fill assumed')
                buy = result.trades[result.trades.side.eq('BUY')].iloc[0]
                if buy.trade_date != entry:
                    raise ValueError('Outcome entry is not the next session')
                final = result.holdings[result.holdings.trade_date.eq(exit_)] if not result.holdings.empty else result.holdings
                exit_cost = 0.
                for holding in final.to_dict('records'):
                    bar = asset_prices[asset_prices.trade_date.eq(exit_) & asset_prices.instrument_id.eq(holding['instrument_id'])]
                    if len(bar) != 1 or not executable(bar.iloc[0].to_dict()):
                        raise ValueError('No executable outcome exit')
                    exit_cost += cost_model.cost(date=exit_,side='SELL',turnover=holding['value'])['total']
                curve = result.equity_curve
                realized = (curve.nav.iloc[-1]-exit_cost)/1_000_000-1
                paid = result.trades.total.sum()+exit_cost
                gross_invested = buy.turnover
                # Restore explicit charges and normalize by deployed gross capital;
                # fractional units and the uninvested cash remainder are retained.
                gross = (curve.nav.iloc[-1]-exit_cost+paid-1_000_000)/gross_invested
                nifty = b.close.iloc[1]/b.open.iloc[0]-1
                tri_return = t.close.iloc[1]/t.close.iloc[0]-1
                wealth = curve[curve.trade_date >= entry].nav/1_000_000
                returns = curve[curve.trade_date >= entry].daily_return
                record = dict(signal_id=signal['signal_id'], horizon_sessions=horizon,
                    outcome_data_as_of=str(pd.Timestamp(as_of).date()),
                    entry_date=str(entry.date()),entry_price=buy.price,exit_date=str(exit_.date()),
                    stock_return=gross,cost_adjusted_return=realized,nifty500_return=nifty,
                    nifty500_tri_return=tri_return,excess_return=gross-nifty,
                    cost_adjusted_excess_return=realized-nifty,
                    total_return_excess=realized-tri_return,
                    maximum_adverse_excursion=min(0.,float(wealth.min()-1)),
                    maximum_favorable_excursion=max(0.,float(wealth.max()-1)),
                    realized_volatility=float(returns.std(ddof=1)*np.sqrt(252)),
                    excursion_basis='COST_ADJUSTED_DAILY_CLOSE_NAV',
                    tri_entry_convention='PRECEDING_CLOSE_NO_OFFICIAL_OPEN_TRI',
                    lifecycle_scenario=lifecycle_scenario,
                    source_manifest_hash=signal['source_manifest_hash'],
                    model_version=signal['model_version'], feature_version=signal['feature_version'],
                    lifecycle_policy_version=signal['lifecycle_policy_version'],
                    portfolio_accounting_version=signal['portfolio_accounting_version'],
                    evidence_policy_version=signal['evidence_policy_version'],
                    validation_level='FORWARD_PAPER_ONLY')
                record['sha256'] = content_hash(record)
                append_record(target,record)
                reports['written'] += 1
            except (ValueError,KeyError,IndexError) as error:
                reports['blocked'].append(dict(signal_id=signal['signal_id'],horizon=horizon,reason=str(error)))
    return reports
