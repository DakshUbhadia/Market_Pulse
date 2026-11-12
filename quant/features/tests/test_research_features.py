import numpy as np
import pandas as pd
import pytest

from quant.features.momentum import momentum_features
from quant.features.matrix import build_feature_matrix, SCORE_FEATURES
from quant.features.normalize import normalize_cross_section
from quant.features.labels import forward_labels
from quant.features.risk import empirical_cvar
from quant.models.factor_v1 import score_factor_v1
from quant.tests.research_fixtures import market_fixture


def test_exact_momentum_formulas():
    close = pd.Series(np.arange(1, 401, dtype=float))
    row = momentum_features(close).iloc[-1]
    assert row.mom_63 == pytest.approx(400/337-1)
    assert row.mom_126_ex_21 == pytest.approx(379/274-1)
    assert row.mom_252_ex_21 == pytest.approx(379/148-1)
    assert row.distance_52w_high == 0


def test_momentum_does_not_use_future_prices():
    prices, benchmark, sessions = market_fixture()
    past = sessions[280]
    original = build_feature_matrix(prices, benchmark, sessions, as_of=past)
    changed = prices.copy()
    changed.loc[changed.trade_date > past, 'adjusted_close'] *= 100
    altered = build_feature_matrix(changed, benchmark, sessions, as_of=past)
    columns = SCORE_FEATURES + ['z_'+name for name in SCORE_FEATURES]
    pd.testing.assert_frame_equal(original[columns], altered[columns])
    pd.testing.assert_series_equal(score_factor_v1(original).percentile_score, score_factor_v1(altered).percentile_score)


def test_feature_lags_are_calendar_sessions_not_observed_rows():
    prices, benchmark, sessions = market_fixture(stocks=1)
    prices = prices[prices.trade_date != sessions[200]]
    result = build_feature_matrix(prices, benchmark, sessions, as_of=sessions[263])
    assert result.mom_63.isna().all()


def test_snapshot_optimization_matches_full_history_features():
    prices, benchmark, sessions = market_fixture(stocks=3, days=410)
    full = build_feature_matrix(prices, benchmark, sessions)
    snapshot = build_feature_matrix(prices, benchmark, sessions, as_of=sessions[-1])
    columns = SCORE_FEATURES + ['z_'+name for name in SCORE_FEATURES] + ['history_sessions']
    pd.testing.assert_frame_equal(snapshot[columns].reset_index(drop=True),
        full.loc[full.as_of == sessions[-1],columns].reset_index(drop=True), rtol=1e-8)


def test_normalization_is_point_in_time_and_eligible_only():
    frame = pd.DataFrame(dict(as_of=[pd.Timestamp('2024-01-01')]*4, value=[1., 2., 3., 1e9],
                              eligible=[True, True, True, False], feature_valid=True))
    first = normalize_cross_section(frame, ['value'])
    future = frame.copy(); future['as_of'] = pd.Timestamp('2024-02-01'); future['value'] *= 1000
    combined = normalize_cross_section(pd.concat([frame, future], ignore_index=True), ['value'])
    pd.testing.assert_series_equal(first.z_value, combined.z_value.iloc[:4])
    assert pd.isna(first.z_value.iloc[-1]) and first.z_value.dropna().between(-3, 3).all()


def test_label_starts_next_session_and_has_exact_63_session_tail():
    prices, benchmark, sessions = market_fixture(stocks=1, days=100)
    result = forward_labels(prices, benchmark, sessions)
    row = result.iloc[0]
    p = prices.set_index('trade_date')
    assert row.entry_date == sessions[1] and row.exit_date == sessions[63]
    assert row.stock_return_63 == pytest.approx(p.loc[sessions[63], 'adjusted_close']/p.loc[sessions[1], 'adjusted_open']-1)
    assert not result.tail(63).label_available.any()


def test_cvar_uses_empirical_tail_not_gaussian_estimate():
    values = np.r_[np.repeat(.01, 95), [-.1, -.2, -.3, -.4, -.5]]
    assert empirical_cvar(values) == pytest.approx(.3)


def test_forward_label_requires_trading_at_entry_and_exit():
    prices,benchmark,sessions=market_fixture(stocks=1,days=100)
    prices.loc[prices.trade_date.isin([sessions[1],sessions[64]]),'volume']=0
    labels=forward_labels(prices,benchmark,sessions)
    assert not labels.loc[labels.as_of.isin([sessions[0],sessions[1]]),'label_available'].any()
    assert labels.loc[labels.as_of==sessions[2],'label_available'].all()


def test_compact_research_preserves_eligible_features_and_requested_labels():
    prices,benchmark,sessions=market_fixture(stocks=3,days=330)
    prices.loc[prices.instrument_id.eq('id-002') & prices.trade_date.lt(sessions[280]),'traded_value']=1
    full=build_feature_matrix(prices,benchmark,sessions)
    compact=build_feature_matrix(prices,benchmark,sessions,eligible_only=True)
    fields=['as_of','instrument_id','eligible','history_sessions']+SCORE_FEATURES+['z_'+name for name in SCORE_FEATURES]
    pd.testing.assert_frame_equal(compact[fields].reset_index(drop=True),
        full.loc[full.eligible,fields].reset_index(drop=True))
    all_labels=forward_labels(prices,benchmark,sessions)
    keys=compact[['as_of','instrument_id']].iloc[::4]
    selected=forward_labels(prices,benchmark,sessions,signal_keys=keys)
    expected=all_labels.merge(keys,on=['as_of','instrument_id'],how='inner')
    pd.testing.assert_frame_equal(selected.reset_index(drop=True),expected[selected.columns].reset_index(drop=True))
