import numpy as np
import pandas as pd

from quant.features.risk import empirical_cvar


def ratio(numerator, denominator):
    return float(numerator/denominator) if np.isfinite(denominator) and denominator > 0 else None


def performance_metrics(curve, benchmark, trades=None):
    if curve.empty:
        raise ValueError('No equity curve')
    frame = curve.set_index('trade_date')
    returns = frame.daily_return
    market = benchmark.reindex(frame.index)
    if returns.isna().any() or market.isna().any():
        raise ValueError('Incomplete return alignment')
    excess = returns-market
    wealth = pd.concat([pd.Series([1.0]), (1+returns).cumprod().reset_index(drop=True)], ignore_index=True)
    drawdown = wealth/wealth.cummax()-1
    total = float((1+returns).prod()-1)
    annual = float((1+total)**(252/len(returns))-1)
    days = max(1, (frame.index[-1]-frame.index[0]).days + 1)
    cagr = float((1+total)**(365.25/days)-1)
    monthly = (1+returns).resample('ME').prod()-1
    yearly = (1+returns).resample('YE').prod()-1
    underwater = drawdown < 0
    duration = underwater.groupby((~underwater).cumsum()).cumsum()
    realized = pd.Series(dtype=float)
    if trades is not None and not trades.empty and 'realized_pnl' in trades:
        realized = trades.loc[trades.side == 'SELL', 'realized_pnl'].dropna()
    result = dict(total_return=total, CAGR=cagr, annualized_return=annual,
        annualized_volatility=float(returns.std(ddof=1)*np.sqrt(252)),
        Sharpe=ratio(returns.mean()*np.sqrt(252), returns.std(ddof=1)),
        Sortino=ratio(returns.mean()*np.sqrt(252), np.sqrt(np.mean(np.minimum(returns, 0)**2))),
        max_drawdown=float(drawdown.min()), Calmar=ratio(cagr, abs(drawdown.min())),
        beta=ratio(returns.cov(market), market.var()),
        information_ratio=ratio(excess.mean()*np.sqrt(252), excess.std(ddof=1)),
        annualized_excess_return=float(excess.mean()*252), turnover=float(frame.turnover.sum()*252/len(frame)),
        hit_rate=float((realized > 0).mean()) if len(realized) else None,
        profit_factor=ratio(realized[realized > 0].sum(), -realized[realized < 0].sum()) if len(realized) else None,
        CVaR=empirical_cvar(returns), worst_month=float(monthly.min()), worst_year=float(yearly.min()),
        drawdown_duration_sessions=int(duration.max()), observations=len(frame))
    rolling = pd.DataFrame({'trade_date': frame.index})
    for years, length in [(1, 252), (3, 756)]:
        stock = (1+returns).rolling(length).apply(np.prod, raw=True)
        bench = (1+market).rolling(length).apply(np.prod, raw=True)
        rolling[f'excess_return_{years}y'] = (stock-bench).to_numpy()
    return result, rolling


def diagnostics(scores, labels):
    if scores.duplicated(['as_of', 'instrument_id']).any() or labels.duplicated(['as_of', 'instrument_id']).any():
        raise ValueError('Duplicate score/label keys')
    joined = scores.merge(labels, on=['as_of', 'instrument_id'], how='left', validate='one_to_one')
    ic, deciles = [], []
    for day, group in joined.groupby('as_of'):
        valid = group[group.label_available.fillna(False)].dropna(subset=['raw_score', 'excess_return_63']).copy()
        if len(valid) < 10 or valid.raw_score.nunique() < 2:
            continue
        correlation = valid.raw_score.rank().corr(valid.excess_return_63.rank())
        ic.append(dict(as_of=day, IC=correlation, observations=len(valid),
                       label_coverage=len(valid)/len(group)))
        valid['decile'] = pd.qcut(valid.raw_score.rank(method='average'), 10, labels=False, duplicates='drop')+1
        for bucket, rows in valid.groupby('decile'):
            deciles.append(dict(as_of=day, decile=int(bucket), absolute_return=rows.stock_return_63.mean(),
                excess_return=rows.excess_return_63.mean(), volatility=rows.future_volatility_63.mean() if 'future_volatility_63' in rows else None,
                observations=len(rows)))
    table = pd.DataFrame(ic, columns=['as_of', 'IC', 'observations', 'label_coverage'])
    values = table.IC.dropna()
    summary = dict(mean_IC=float(values.mean()) if len(values) else None,
        median_IC=float(values.median()) if len(values) else None,
        IC_std=float(values.std(ddof=1)) if len(values) > 1 else None,
        ICIR=ratio(values.mean(), values.std(ddof=1)) if len(values) > 1 else None,
        positive_IC_fraction=float((values > 0).mean()) if len(values) else None,
        label_coverage=float(joined.loc[joined.exit_date.notna(), 'label_available'].fillna(False).mean())
            if joined.exit_date.notna().any() else 0,
        censored_tail_rows=int(joined.exit_date.isna().sum()),
        unresolved_mature_labels=int((joined.exit_date.notna() & ~joined.label_available.fillna(False)).sum()))
    return table, pd.DataFrame(deciles), summary
