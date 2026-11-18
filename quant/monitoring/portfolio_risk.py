"""Observed portfolio volatility, cash and concentration limits."""
import numpy as np
import pandas as pd


def portfolio_risk(curve, *, cluster_weights, target_volatility=.15,
                   max_cluster_weight=.25, lookback=63):
    returns = pd.to_numeric(curve.daily_return, errors='coerce').tail(lookback)
    clusters = pd.Series(cluster_weights, dtype=float)
    valid = (len(returns) >= lookback and np.isfinite(returns).all() and len(clusters)
             and np.isfinite(clusters).all() and clusters.ge(0).all() and clusters.sum() <= 1+1e-9)
    volatility = float(returns.std(ddof=1)*np.sqrt(252)) if valid else None
    concentration = float(clusters.max()) if valid else None
    cash = float((curve.cash/curve.nav).iloc[-1]) if len(curve) and {'cash', 'nav'} <= set(curve) else None
    return dict(status=('PASS' if volatility <= target_volatility*1.25 and concentration <= max_cluster_weight
                        else 'ALERT') if valid else 'UNASSESSED',
        realized_volatility=volatility, target_volatility=target_volatility,
        max_cluster_concentration=concentration, cash_weight=cash, action='REVIEW_ONLY')
