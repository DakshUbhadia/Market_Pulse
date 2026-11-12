from datetime import date

import pandas as pd


def rolling_windows(*, first_test_year=2016, last_test_year=2026, training_years=6):
    return [dict(train_start=date(year-training_years, 1, 1), train_end=date(year-1, 12, 31),
                 test_start=date(year, 1, 1), test_end=date(year, 12, 31))
            for year in range(first_test_year, last_test_year+1)]


def purged_training_labels(labels, window, sessions, *, embargo_sessions=63):
    calendar = pd.DatetimeIndex(pd.to_datetime(sessions))
    before = calendar[calendar < pd.Timestamp(window['test_start'])]
    if len(before) <= embargo_sessions:
        return labels.iloc[:0].copy()
    cutoff = before[-embargo_sessions-1]
    return labels[(labels.as_of >= pd.Timestamp(window['train_start']))
                  & (labels.as_of <= pd.Timestamp(window['train_end']))
                  & labels.label_available & (labels.exit_date <= cutoff)].copy()


def walk_forward(prices, scores, labels, sessions, *, windows=None, portfolio=None, cost_model=None):
    from quant.backtest.engine import run_backtest
    output = []
    for window in windows or rolling_windows():
        if pd.Timestamp(window['test_start']) > pd.Timestamp(max(sessions)):
            continue
        train = purged_training_labels(labels, window, sessions)
        # V1 weights are fixed before observing any test outcome; no fitted model or random folds.
        result = run_backtest(prices, scores, sessions, start=window['test_start'], end=window['test_end'],
                               portfolio=portfolio, cost_model=cost_model)
        test_scores = scores[scores.as_of.between(pd.Timestamp(window['test_start']), pd.Timestamp(window['test_end']))]
        output.append(dict(window=window, train_labels=len(train), result=result, scores=test_scores,
                           method='FIXED_PREDECLARED_WEIGHTS_NO_TEST_OPTIMIZATION', embargo_sessions=63))
    return output
