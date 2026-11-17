"""Trailing-return single-link hierarchical clusters, cut at a fixed distance.

At a fixed cut, single-link clustering equals connected components of the graph
whose edges have distance <= threshold. This computes that cut without an
additional ML dependency. Cluster IDs are local to each as_of cross section.
"""
import numpy as np
import pandas as pd

from quant.universe.eligible import session_index

CLUSTER_VERSION = 'returns_single_link_pairwise_252_1.1.0'
MIN_CLUSTER_OBSERVATIONS = 220


def return_clusters(prices, sessions, as_of, *, instrument_ids=None, lookback=252,
                    distance_threshold=1.0, min_observations=None, return_pairs=False):
    minimum = min_observations if min_observations is not None else min(MIN_CLUSTER_OBSERVATIONS, lookback)
    if (lookback < 2 or not 2 <= minimum <= lookback or not np.isfinite(distance_threshold)
            or not 0 <= distance_threshold <= 2):
        raise ValueError('Invalid cluster lookback, overlap or distance cut')
    dates = session_index(sessions)
    dates = dates[dates <= pd.Timestamp(as_of)][-(lookback+1):]
    rows = prices[(pd.to_datetime(prices.trade_date) <= pd.Timestamp(as_of)) & prices.series.eq('EQ')].copy()
    if instrument_ids is not None:
        rows = rows[rows.instrument_id.isin(instrument_ids)]
    rows = rows[rows.instrument_id.notna() & pd.to_datetime(rows.trade_date).isin(dates)]
    if rows.duplicated(['trade_date', 'instrument_id']).any():
        raise ValueError('Ambiguous cluster input bars')
    rows.loc[rows.adjustment_status.ne('OK'), 'adjusted_close'] = np.nan
    panel = rows.pivot(index='trade_date', columns='instrument_id', values='adjusted_close').reindex(dates)
    returns = panel.where(panel > 0).pct_change(fill_method=None).iloc[1:]
    counts = returns.count()
    candidates = sorted(returns.columns[counts.ge(minimum) & returns.std().gt(1e-12)])
    observed = returns[candidates].notna().astype('int64')
    overlap = observed.T.dot(observed)
    correlation = returns[candidates].corr(min_periods=minimum).clip(-1, 1)
    sufficient = overlap.ge(minimum) & correlation.notna()
    # Missing pairwise coverage must not masquerade as diversification. Require
    # usable overlap against every other candidate before assigning a cluster.
    names = [name for name in candidates if sufficient.loc[name].all()]
    parent = list(range(len(names)))

    def root(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    if names:
        distance = np.sqrt(2 * (1-correlation.loc[names,names].to_numpy()))
        for i, j in zip(*np.where(np.triu(distance <= distance_threshold, k=1))):
            a, b = root(i), root(j)
            parent[max(a, b)] = min(a, b)
    labels = {name: f'C{root(i):04d}' for i, name in enumerate(names)}
    identities = sorted(set(instrument_ids) if instrument_ids is not None else set(panel.columns))
    result = pd.DataFrame([dict(as_of=pd.Timestamp(as_of), instrument_id=name,
        cluster_id=labels.get(name), cluster_version=CLUSTER_VERSION,
        status='ASSESSED' if name in labels else 'UNASSESSED',
        reason='' if name in labels else ('INSUFFICIENT_OVERLAP' if name in candidates else 'INSUFFICIENT_HISTORY'),
        observed_returns=int(counts.get(name,0)), min_observations=minimum,
        lookback_sessions=lookback, distance_threshold=distance_threshold) for name in identities],
        columns=['as_of','instrument_id','cluster_id','cluster_version','status','reason',
                 'observed_returns','min_observations','lookback_sessions','distance_threshold'])
    if not return_pairs:
        return result
    pairs = pd.DataFrame([dict(left=a,right=b,overlap=int(overlap.loc[a,b]),
        correlation=correlation.loc[a,b],pair_status='ASSESSED' if sufficient.loc[a,b] else 'INSUFFICIENT_OVERLAP')
        for i,a in enumerate(candidates) for b in candidates[i+1:]],
        columns=['left','right','overlap','correlation','pair_status'])
    return result,pairs


def cluster_exposure(weights, clusters):
    if weights.index.has_duplicates or not np.isfinite(weights).all() or (weights < 0).any() or weights.sum() > 1+1e-8:
        raise ValueError('Invalid cluster exposure weights')
    if clusters.instrument_id.duplicated().any():
        raise ValueError('Duplicate cluster membership')
    membership = clusters.set_index('instrument_id').cluster_id.reindex(weights.index)
    unknown = float(weights[membership.isna()].sum())
    grouped = weights.groupby(membership.fillna('UNKNOWN')).sum()
    invested = float(grouped.sum())
    return dict(max_cluster_weight=float(grouped.max()) if len(grouped) else 0.0,
        number_of_clusters=int((grouped.drop('UNKNOWN', errors='ignore') > 0).sum()),
        effective_number_of_clusters=float(invested**2 / grouped.pow(2).sum()) if invested else 0.0,
        unknown_weight=unknown, assessed=bool(invested > 0 and unknown == 0),
        cluster_weights=grouped.to_dict())


def rebalance_cluster_diagnostics(prices, scores, sessions, holdings, equity_curve, *, distance_threshold=1.0):
    """Cluster the signal-date universe; measure actual holdings after each rebalance."""
    from quant.backtest.engine import monthly_signal_dates
    dates = session_index(sessions)
    signal_dates = monthly_signal_dates(dates)
    memberships, reports = [], []
    if holdings.empty:
        return pd.DataFrame(), pd.DataFrame()
    held_by_day = {pd.Timestamp(day): group for day, group in holdings.groupby('trade_date')}
    nav_by_day = equity_curve.set_index('trade_date').nav
    for i, day in enumerate(dates[1:], start=1):
        signal = dates[i-1]
        if signal not in signal_dates or day not in held_by_day:
            continue
        held = held_by_day[day]
        ids = set(scores.loc[scores.as_of.eq(signal), 'instrument_id']) | set(held.instrument_id)
        cluster = return_clusters(prices, dates, signal, instrument_ids=ids, distance_threshold=distance_threshold)
        memberships.append(cluster)
        weights = held.set_index('instrument_id').value / nav_by_day.loc[day]
        reports.append(dict(as_of=signal, execution_date=day, **cluster_exposure(weights, cluster)))
    return (pd.concat(memberships, ignore_index=True) if memberships else pd.DataFrame(), pd.DataFrame(reports))


def cluster_sensitivity(prices, scores, sessions, holdings, equity_curve, *, thresholds=(.8,1.,1.2)):
    """Predeclared diagnostic cuts; no portfolio constraints or selected best cut."""
    reports = []
    for cut in thresholds:
        _, exposure = rebalance_cluster_diagnostics(prices,scores,sessions,holdings,equity_curve,
                                                   distance_threshold=cut)
        if not exposure.empty:
            reports.append(exposure.assign(distance_threshold=cut,cluster_version=CLUSTER_VERSION))
    return pd.concat(reports,ignore_index=True) if reports else pd.DataFrame()
