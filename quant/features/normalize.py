import numpy as np
import pandas as pd


def normalize_cross_section(frame, columns, *, lower=.01, upper=.99):
    if not 0 <= lower < upper <= 1:
        raise ValueError('Invalid winsorization bounds')
    result = frame.copy()
    for name in columns:
        result['z_' + name] = np.nan
    for _, group in result[result.eligible & result.feature_valid].groupby('as_of'):
        for name in columns:
            values = group[name].replace([np.inf, -np.inf], np.nan).dropna()
            if values.empty:
                continue
            clipped = values.clip(values.quantile(lower), values.quantile(upper))
            median = clipped.median()
            mad = (clipped - median).abs().median()
            z = (clipped - median) / (1.4826 * mad) if mad > 0 else pd.Series(0.0, index=values.index)
            result.loc[z.index, 'z_' + name] = z.clip(-3, 3)
    return result
