"""Reproducible top/bottom/middle review samples; never assert manual approval."""
import numpy as np
import pandas as pd


def ranking_review_sample(scores, *, count=30, seed=7):
    if count < 1 or scores.instrument_id.duplicated().any():
        raise ValueError('Review requires a unique cross section and positive sample size')
    ordered = scores.sort_values(['rank','instrument_id']).reset_index(drop=True)
    top = ordered.head(count).assign(review_group='TOP')
    bottom = ordered[~ordered.instrument_id.isin(top.instrument_id)].tail(count).assign(review_group='BOTTOM')
    middle = ordered[~ordered.instrument_id.isin(set(top.instrument_id) | set(bottom.instrument_id))]
    if len(middle):
        selected = np.random.default_rng(seed).choice(len(middle), size=min(count,len(middle)),replace=False)
        middle = middle.iloc[sorted(selected)]
    middle = middle.assign(review_group='MIDDLE_RANDOM')
    result = pd.concat([top,bottom,middle],ignore_index=True)
    result['review_seed'] = seed
    result['review_status'] = 'NEEDS_MANUAL_REVIEW'
    for check in ('identity','instrument_type','ipo_age','liquidity','corporate_actions','lifecycle',
                  'adjusted_continuity','volatility','adv','duplicates'):
        result['review_'+check] = 'UNREVIEWED'
    return result
