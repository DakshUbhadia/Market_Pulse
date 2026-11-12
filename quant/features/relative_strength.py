import pandas as pd


def relative_strength(close, benchmark):
    benchmark = benchmark.reindex(close.index)
    return pd.DataFrame({f'rs_nifty500_{days}': (close / close.shift(days) - 1)
                         - (benchmark / benchmark.shift(days) - 1) for days in (63, 126)})
