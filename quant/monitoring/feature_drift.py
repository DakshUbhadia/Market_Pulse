"""Fixed reference-bin population stability and cross-section rank turnover."""
import numpy as np
import pandas as pd


def feature_drift(reference, current, *, features, threshold=.2, minimum_observations=20):
    rows = []
    for feature in features:
        old, new = [pd.to_numeric(f.get(feature, pd.Series(dtype=float)), errors='coerce').replace(
            [np.inf, -np.inf], np.nan).dropna() for f in (reference, current)]
        if min(len(old), len(new)) < minimum_observations:
            rows.append(dict(feature=feature, status='UNASSESSED', psi=None))
            continue
        # Fixed bins come entirely from reference history, with infinite tails.
        interior = np.unique(np.quantile(old, np.linspace(0, 1, 11)))
        edges = np.r_[-np.inf, interior, np.inf]
        a, b = [np.histogram(v, bins=edges)[0].astype(float) for v in (old, new)]
        a, b = [(v+.5)/(v.sum()+.5*len(v)) for v in (a, b)]
        psi = float(((b-a)*np.log(b/a)).sum())
        rows.append(dict(feature=feature, status='ALERT' if psi > threshold else 'PASS', psi=psi))
    return dict(status='ALERT' if any(r['status'] == 'ALERT' for r in rows) else
                'PASS' if rows and all(r['status'] == 'PASS' for r in rows) else 'UNASSESSED',
                features=rows, threshold=threshold, action='REVIEW_ONLY', automatic_retraining=False)


def rank_turnover(previous, current, *, top_count=25):
    if previous.instrument_id.duplicated().any() or current.instrument_id.duplicated().any():
        raise ValueError('Rank turnover requires unique cross sections')
    a, b = [set(f.sort_values('rank').head(top_count).instrument_id) for f in (previous, current)]
    return 1-len(a & b)/max(len(a), len(b)) if a and b else None
