"""Ledoit-Wolf on complete observed trailing returns; no price filling."""
import numpy as np
import pandas as pd


def shrinkage_covariance(returns, as_of, *, lookback=252, min_observations=220):
    if not 2 <= min_observations <= lookback or returns.empty or not returns.columns.is_unique:
        raise ValueError('Invalid covariance history or observation policy')
    frame = returns.copy()
    frame.index = pd.to_datetime(frame.index)
    if frame.index.has_duplicates or not frame.index.is_monotonic_increasing:
        raise ValueError('Return sessions must be unique and ordered')
    frame = frame.loc[frame.index <= pd.Timestamp(as_of)].tail(lookback)
    frame = frame.replace([np.inf,-np.inf],np.nan).dropna(how='any')
    if len(frame) < min_observations or (frame.std(ddof=0) <= 0).any():
        raise ValueError('Insufficient jointly observed covariance history')
    # Ledoit & Wolf (2004), shrinkage toward trace(S)/p times the identity.
    # The moment estimator is expressed directly in NumPy to avoid an ML
    # runtime dependency for covariance estimation.
    x = frame.to_numpy(dtype=float)
    x = x-x.mean(axis=0)
    n,p = x.shape
    empirical = x.T@x/n
    target = np.eye(p)*np.trace(empirical)/p
    distance = np.square(empirical-target).sum()/p
    variance = (np.square(np.square(x).sum(axis=1)).mean()-np.square(empirical).sum())/(n*p)
    shrinkage = float(np.clip(variance/distance,0,1)) if distance > 0 and p > 1 else 0.
    matrix = pd.DataFrame(((1-shrinkage)*empirical+shrinkage*target)*252, index=frame.columns, columns=frame.columns)
    if not np.isfinite(matrix).all().all() or np.linalg.eigvalsh(matrix).min() <= 0:
        raise ValueError('Invalid covariance estimate')
    return matrix, dict(observations=len(frame), first_session=str(frame.index.min()),
                        last_session=str(frame.index.max()), shrinkage=shrinkage,
                        annualization=252, estimator='LedoitWolf')
