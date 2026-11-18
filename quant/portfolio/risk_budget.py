"""Constrained risk allocation over declared rank-selected names, with cash."""
import numpy as np
import pandas as pd
from quant.portfolio.constraints import RiskPolicy, capacity_report

from quant.version import PORTFOLIO_RISK_VERSION


def allocate_risk(covariance, previous, adv, clusters, *, nav, selected=None, policy=None):
    from scipy.optimize import minimize
    policy = policy or RiskPolicy()
    names = covariance.index
    if (not names.is_unique or not len(names) or not names.equals(covariance.columns)
            or not previous.index.is_unique or not adv.index.is_unique or not clusters.index.is_unique
            or not set(previous[previous > 0].index).issubset(names)):
        raise ValueError('Covariance must cover all selected and currently held names')
    sigma = covariance.to_numpy(dtype=float)
    if (not np.isfinite(sigma).all() or not np.allclose(sigma,sigma.T)
            or np.linalg.eigvalsh(sigma).min() <= 0):
        raise ValueError('Covariance must be symmetric positive definite')
    old = previous.reindex(names).fillna(0).astype(float)
    liquidity, groups = adv.reindex(names), clusters.reindex(names)
    if (not np.isfinite(old).all() or (old < 0).any() or old.sum() > 1+1e-9
            or groups.isna().any()):
        raise ValueError('Invalid prior holdings or missing dated clusters')
    # Validates capital and ADV before calculating executable weight changes.
    capacity_report(old,old,liquidity,nav,fraction=policy.adv_fraction)
    step = policy.adv_fraction*liquidity.to_numpy()/nav
    lower = np.maximum(0,old.to_numpy()-step)
    selected = set(names) if selected is None else set(selected)
    if not selected.issubset(names):
        raise ValueError('Unknown selected name')
    cap = np.array([policy.max_weight if n in selected else 0. for n in names])
    upper = np.minimum(cap,old.to_numpy()+step)
    if (lower > upper+1e-10).any():
        raise ValueError('Infeasible mandatory exit or position cap under ADV constraints')
    masks = [groups.eq(g).to_numpy(dtype=float) for g in sorted(set(groups))]
    constraints = [dict(type='ineq',fun=lambda w: policy.gross_exposure-w.sum()),
                   dict(type='ineq',fun=lambda w: policy.target_volatility**2-w@sigma@w)]
    constraints.extend(dict(type='ineq',fun=lambda w,m=m: policy.max_cluster_weight-m@w) for m in masks)
    bounds = list(zip(lower,upper))
    # Cash absorbs constraints. First determine feasible gross exposure, then
    # minimize risk plus turnover at that exposure; variance alone chooses cash.
    exposure = minimize(lambda w:-w.sum(),lower,bounds=bounds,constraints=constraints,
                        method='SLSQP',options=dict(ftol=1e-11,maxiter=1000))
    if not exposure.success:
        raise ValueError('Infeasible risk budget: '+exposure.message)
    gross = float(exposure.x.sum())
    equality = dict(type='eq',fun=lambda w:w.sum()-gross)
    result = minimize(lambda w: w@sigma@w+policy.turnover_penalty*np.abs(w-old.to_numpy()).sum(),
                      exposure.x,bounds=bounds,constraints=constraints+[equality],
                      method='SLSQP',options=dict(ftol=1e-11,maxiter=1000))
    if not result.success:
        raise ValueError('Risk optimizer failed: '+result.message)
    w = result.x
    if (any(c['fun'](w) < -1e-7 for c in constraints) or abs(w.sum()-gross)>1e-7
            or (w < lower-1e-7).any() or (w > upper+1e-7).any()):
        raise ValueError('Risk optimizer returned a constraint violation')
    weights = pd.Series(w,index=names,name='weight')
    capacity = capacity_report(weights,old,liquidity,nav,fraction=policy.adv_fraction)
    if not capacity.capacity_passed.all():
        raise ValueError('Risk allocation exceeds capacity')
    return weights, dict(version=PORTFOLIO_RISK_VERSION, cash_weight=max(0.,1-float(w.sum())),
        annualized_volatility=float(np.sqrt(w@sigma@w)), gross_exposure=float(w.sum()),
        turnover=float(np.abs(w-old.to_numpy()).sum()), capacity=capacity.to_dict('index'))
