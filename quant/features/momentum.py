import pandas as pd


def momentum_features(close, *, long_lookback=252, medium_lookback=126):
    return pd.DataFrame({
        'mom_21': close / close.shift(21) - 1,
        'mom_63': close / close.shift(63) - 1,
        'mom_126_ex_21': close.shift(21) / close.shift(medium_lookback) - 1,
        'mom_252_ex_21': close.shift(21) / close.shift(long_lookback) - 1,
        'distance_52w_high': close / close.rolling(252, min_periods=252).max() - 1,
    })
