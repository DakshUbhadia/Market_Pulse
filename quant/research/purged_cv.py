"""Expanding date-based folds; overlapping label intervals never cross a split."""
import numpy as np
import pandas as pd


def date_balanced_weights(dates):
    values = pd.Series(pd.to_datetime(dates)).reset_index(drop=True)
    if values.isna().any():
        raise ValueError('Missing sample date')
    return (1/values.groupby(values).transform('size')).to_numpy()


def purged_walk_forward(samples, sessions, *, min_train_sessions, test_sessions,
                        embargo_sessions=63):
    dates = pd.DatetimeIndex(pd.to_datetime(sessions))
    if (dates.has_duplicates or not dates.is_monotonic_increasing or dates.isna().any()
            or min_train_sessions < 2 or test_sessions < 1 or embargo_sessions < 0):
        raise ValueError('Invalid walk-forward session policy')
    signal = pd.to_datetime(samples.as_of).reset_index(drop=True)
    exits = pd.to_datetime(samples.exit_date).reset_index(drop=True)
    if (signal.isna().any() or exits.isna().any() or (exits < signal).any()
            or not signal.isin(dates).all() or not exits.isin(dates).all()):
        raise ValueError('Mature label intervals must lie on the supplied exchange calendar')
    for start in range(min_train_sessions+embargo_sessions,len(dates),test_sessions):
        test_start = dates[start]
        test_end = dates[min(start+test_sessions-1,len(dates)-1)]
        train_end = dates[start-embargo_sessions-1]
        train = np.flatnonzero((signal <= train_end) & (exits <= train_end))
        test = np.flatnonzero(signal.between(test_start,test_end))
        if (len(train) and len(test)
                and dates.get_loc(signal.iloc[train].max())-dates.get_loc(signal.iloc[train].min())+1 >= min_train_sessions):
            yield train,test


def nested_purged_walk_forward(samples, sessions, *, outer_train_sessions, outer_test_sessions,
                               inner_train_sessions, inner_test_sessions, embargo_sessions=63):
    """Return absolute sample positions; inner folds use only outer training rows."""
    calendar=pd.DatetimeIndex(pd.to_datetime(sessions))
    for outer_train,outer_test in purged_walk_forward(samples,calendar,
            min_train_sessions=outer_train_sessions,test_sessions=outer_test_sessions,
            embargo_sessions=embargo_sessions):
        training=samples.iloc[outer_train].reset_index(drop=True)
        last=pd.to_datetime(training.exit_date).max()
        inner=[]
        for train,test in purged_walk_forward(training,calendar[calendar<=last],
                min_train_sessions=inner_train_sessions,test_sessions=inner_test_sessions,
                embargo_sessions=embargo_sessions):
            inner.append((outer_train[train],outer_train[test]))
        if inner:
            yield outer_train,outer_test,inner
