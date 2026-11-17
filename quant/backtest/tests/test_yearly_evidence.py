import pandas as pd
import pytest

from quant.backtest.report import evaluate_evidence


def test_yearly_concentration_compounds_volatile_returns():
    dates = pd.to_datetime(['2021-01-04','2021-01-05','2022-01-04','2023-01-04'])
    curve = pd.DataFrame(dict(trade_date=dates,daily_return=[1.,-.5,.1,.1]))
    evidence = evaluate_evidence({}, {}, pd.DataFrame(), {},curve,pd.Series(0.,index=dates),costs_verified=False)
    # First year's +100%, -50% compounds to zero; remaining years contribute equally.
    assert evidence['largest_positive_year_fraction'] == pytest.approx(.5)
