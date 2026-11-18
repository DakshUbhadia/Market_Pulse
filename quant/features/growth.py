"""YoY growth compares matching quarters and requires positive base earnings."""
import numpy as np
from quant.features.fundamentals import ratio

GROWTH_FIELDS = {'revenue_yoy': 1, 'pat_yoy': 1}


def growth_features(row):
    result = {name: np.nan for name in GROWTH_FIELDS}
    if row.get('quarter_fresh'):
        for field in ('revenue','pat'):
            result[field+'_yoy'] = ratio(row.get('quarter_'+field), row.get('prior_quarter_'+field))-1
    return result
