import numpy as np
import pandas as pd
import pytest

from quant.risk.clusters import return_clusters, cluster_exposure


def fixture():
    dates = pd.bdate_range('2024-01-01', periods=300)
    moves = np.random.default_rng(7).normal(0, .01, len(dates))
    frames = [pd.DataFrame(dict(trade_date=dates, instrument_id=name, series='EQ',
        adjusted_close=100*np.exp(np.cumsum(sign*moves)), adjustment_status='OK'))
        for name, sign in [('a',1), ('b',1), ('c',-1)]]
    return pd.concat(frames), dates


def test_correlated_names_cluster_and_future_rows_cannot_change_membership():
    prices, dates = fixture()
    one = return_clusters(prices, dates, dates[260]).set_index('instrument_id')
    assert one.loc['a','cluster_id'] == one.loc['b','cluster_id']
    assert one.loc['a','cluster_id'] != one.loc['c','cluster_id']
    prices.loc[prices.trade_date > dates[260], 'adjusted_close'] = 999999
    pd.testing.assert_frame_equal(one, return_clusters(prices, dates, dates[260]).set_index('instrument_id'))
    exposure = cluster_exposure(pd.Series(dict(a=.3,b=.3,c=.4)), one.reset_index())
    assert exposure['max_cluster_weight'] == pytest.approx(.6)
    assert exposure['number_of_clusters'] == 2
    assert exposure['effective_number_of_clusters'] == pytest.approx(1/(.6**2+.4**2))


def test_missing_history_is_explicit_and_never_filled():
    prices, dates = fixture()
    prices = prices[~(prices.instrument_id.eq('b') & prices.trade_date.eq(dates[100]))]
    clusters = return_clusters(prices, dates, dates[260], instrument_ids=['a','b','c','missing'])
    result = cluster_exposure(pd.Series(dict(a=.2,b=.2,missing=.2)), clusters)
    assert not result['assessed'] and result['unknown_weight'] == pytest.approx(.4)
