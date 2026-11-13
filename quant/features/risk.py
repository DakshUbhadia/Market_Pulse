import numpy as np
import pandas as pd


def empirical_cvar(returns, tail=.05):
    values = np.asarray(returns, dtype=float)
    if not len(values) or not np.isfinite(values).all():
        return np.nan
    count = max(1, int(np.ceil(len(values) * tail)))
    return max(0.0, -float(np.partition(values, count - 1)[:count].mean()))


def risk_features(close, benchmark):
    returns = close.pct_change(fill_method=None)
    market = benchmark.reindex(close.index).pct_change(fill_method=None)
    result = pd.DataFrame({f'vol_{days}': returns.rolling(days).std(ddof=1) * np.sqrt(252) for days in (20, 63, 252)})
    result['downside_vol_63'] = returns.clip(upper=0).pow(2).rolling(63).mean().pow(.5) * np.sqrt(252)
    result['beta_252'] = returns.rolling(252).cov(market) / market.rolling(252).var().replace(0, np.nan)
    result['max_drawdown_252'] = close.rolling(252).apply(lambda values: np.min(values / np.maximum.accumulate(values) - 1), raw=True)
    result['cvar_95_252'] = returns.rolling(252).apply(empirical_cvar, raw=True)
    return result
