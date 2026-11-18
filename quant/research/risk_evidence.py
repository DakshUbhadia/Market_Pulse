"""Comparable realized cash, liquidity and risk diagnostics for every arm."""
import numpy as np
import pandas as pd


def risk_evidence(result, features, budgets, policy, capital, benchmark_returns=None):
    curve, trades = result.equity_curve, result.trades
    capacity = None
    max_participation = None
    if not trades.empty:
        dated = trades.merge(features[['as_of', 'instrument_id', 'adv60']].rename(columns={'as_of': 'signal_date'}),
            on=['signal_date', 'instrument_id'], how='left', validate='many_to_one')
        if dated.adv60.isna().any() or not np.isfinite(dated.adv60).all() or dated.adv60.le(0).any():
            raise ValueError('Realized orders lack dated liquidity evidence')
        participation = dated.turnover/dated.adv60
        capacity = int(participation.gt(policy.adv_fraction+1e-9).sum())
        max_participation = float(participation.max())
    orders = result.target_orders
    assessed = len(orders) and orders.unfilled_target_weight.notna().all()
    cash_drag = None
    if benchmark_returns is not None and len(curve):
        market = benchmark_returns.reindex(pd.to_datetime(curve.trade_date))
        if market.notna().all():
            cash_drag = float(((curve.cash/curve.nav).shift(1).fillna(1).to_numpy()*market.to_numpy()).sum())
    return dict(capital_scenario=capital, capacity_violations=capacity if capacity is not None else 0,
        max_realized_participation=max_participation,
        mean_cash_weight=float((curve.cash/curve.nav).mean()) if 'cash' in curve else None,
        realized_volatility=float(curve.daily_return.std(ddof=1)*252**.5), target_volatility=policy.target_volatility,
        target_volatility_scope='RISK_BUDGETED_ARM_ONLY',
        unfilled_target_weight=float(orders.groupby('trade_date').unfilled_target_weight.sum().mean()) if assessed else None,
        unfilled_status='ASSESSED_MEAN_REBALANCE_TARGET_SHORTFALL' if assessed else 'UNASSESSED_MISSING_EXECUTABLE_MARKS_OR_NO_TARGETS',
        skipped_orders=len(result.skipped_orders),
        max_cluster_target_weight=max((r.get('max_cluster_weight', 0) for r in budgets), default=None),
        impact_sensitivity='SEE_IDENTICAL_1.5X_AND_2X_COST_STRESS',
        cash_drag=cash_drag, cash_drag_status='SUM_PRIOR_CASH_WEIGHT_TIMES_MATCHED_BENCHMARK_RETURN_PROXY')
