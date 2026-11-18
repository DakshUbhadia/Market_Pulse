"""Compare matured factor IC observations with frozen reference evidence."""
import numpy as np
import pandas as pd


def factor_ic_drift(reference, current, *, as_of, min_observations=12, max_deterioration=.03):
    # Ignore outcomes whose horizon has not matured at the reporting cutoff.
    current = current[pd.to_datetime(current.exit_date).le(pd.Timestamp(as_of))]
    rows = []
    for block, old in reference.groupby('block'):
        new = current[current.block.eq(block)]
        values = pd.to_numeric(new.IC, errors='coerce').replace([np.inf, -np.inf], np.nan).dropna()
        ref = pd.to_numeric(old.IC, errors='coerce').replace([np.inf, -np.inf], np.nan).dropna()
        enough = len(values) >= min_observations and len(ref) >= min_observations
        delta = float(values.mean()-ref.mean()) if enough else None
        rows.append(dict(block=block, observations=len(values), mean_ic_change=delta,
            status=('ALERT' if delta < -max_deterioration else 'PASS') if enough else 'UNASSESSED'))
    return dict(factors=rows, action='REVIEW_ONLY', automatic_retraining=False)
