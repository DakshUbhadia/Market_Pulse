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
    assert not result['assessed'] and result['unknown_weight'] == pytest.approx(.2)
    assert clusters.set_index('instrument_id').loc['b','status'] == 'ASSESSED'


def test_pairwise_overlap_is_observed_and_sparse_pairs_remain_unassessed():
    prices,dates = fixture()
    # Each name has >220 returns, but disjoint holes reduce the pair overlap below 220.
    prices = prices[~((prices.instrument_id.eq('a') & prices.trade_date.isin(dates[30:50]))
        | (prices.instrument_id.eq('b') & prices.trade_date.isin(dates[90:110])))]
    clusters,pairs = return_clusters(prices,dates,dates[260],return_pairs=True)
    assert pairs.query("left == 'a' and right == 'b'").pair_status.iloc[0] == 'INSUFFICIENT_OVERLAP'
    assert clusters.set_index('instrument_id').loc['a','status'] == 'UNASSESSED'
    assert clusters.set_index('instrument_id').loc['b','reason'] == 'INSUFFICIENT_OVERLAP'


def test_single_link_chaining_is_visible_under_predeclared_distance_cuts():
    dates = pd.bdate_range('2024-01-01',periods=300)
    rng = np.random.default_rng(11)
    a,c = rng.normal(0,.01,(2,len(dates)))
    b = .6*a+.8*c
    prices = pd.concat([pd.DataFrame(dict(trade_date=dates,instrument_id=name,series='EQ',
        adjusted_close=100*np.exp(np.cumsum(moves)),adjustment_status='OK')) for name,moves in [('a',a),('b',b),('c',c)]])
    tight = return_clusters(prices,dates,dates[-1],distance_threshold=.8)
    loose = return_clusters(prices,dates,dates[-1],distance_threshold=1.2)
    assert tight.cluster_id.nunique() > loose.cluster_id.nunique()
    assert loose.cluster_id.nunique() == 1
