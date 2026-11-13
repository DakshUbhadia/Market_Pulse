from datetime import date

import numpy as np
import pandas as pd
import pytest

from quant.backtest.costs import CostModel, CostSchedule
from quant.backtest.engine import run_backtest, monthly_signal_dates
from quant.backtest.portfolio import PortfolioConfig, capped_inverse_volatility
from quant.backtest.metrics import performance_metrics, diagnostics
from quant.backtest.bootstrap import block_bootstrap
from quant.backtest.walk_forward import rolling_windows, purged_training_labels
from quant.tests.research_fixtures import market_fixture, execution_scores


def zero_cost():
    schedule = CostSchedule(date(2024,1,1), stt_rate=0, exchange_rate=0, ipft_rate=0, sebi_rate=0,
                            gst_rate=0, stamp_buy=0, stamp_sell=0, dp_sell=0)
    return CostModel(slippage_bps=0, schedules=(schedule,))


def test_next_session_open_execution_and_no_same_close_fills():
    prices, _, sessions = market_fixture(stocks=2, days=45, start='2024-10-01')
    signal = min(monthly_signal_dates(sessions))
    execution = sessions[sessions.get_loc(signal)+1]
    prices.loc[prices.trade_date == execution, 'adjusted_open'] = 200
    result = run_backtest(prices, execution_scores(prices), sessions,
        portfolio=PortfolioConfig(holdings=2, max_weight=.5, entry_percentile=0, exit_percentile=0), cost_model=zero_cost())
    first = result.trades[result.trades.trade_date == execution]
    assert len(first) == 2 and first.price.eq(200).all()
    assert (result.trades.trade_date > result.trades.signal_date).all()
    assert result.equity_curve.cash.ge(-1e-8).all()


def test_unquoted_delisting_holding_is_not_silently_dropped():
    prices, _, sessions = market_fixture(stocks=2, days=45, start='2024-10-01')
    scores = execution_scores(prices)
    prices = prices[~((prices.instrument_id == 'id-001') & (prices.trade_date == sessions[26]))]
    with pytest.raises(ValueError, match='Unvalued holding'):
        run_backtest(prices, scores, sessions, cost_model=zero_cost())


def test_missing_open_cannot_fill_at_a_future_price():
    prices, _, sessions = market_fixture(stocks=1, days=45, start='2024-10-01')
    signal = min(monthly_signal_dates(sessions)); execution = sessions[sessions.get_loc(signal)+1]
    prices.loc[prices.trade_date == execution, 'volume'] = 0
    result = run_backtest(prices, execution_scores(prices), sessions, end=execution, cost_model=zero_cost())
    assert result.trades.empty and result.equity_curve.nav.eq(1_000_000).all()


def test_inverse_volatility_caps_and_cash_when_capacity_is_small():
    weights = capped_inverse_volatility(pd.Series([.01,.2,.3,.4], index=list('abcd')), cap=.3)
    assert weights.max() <= .3 and weights.sum() == pytest.approx(1)
    small = capped_inverse_volatility(pd.Series([.1,.2], index=['a','b']))
    assert small.max() <= .05 and small.sum() == pytest.approx(.1)


def test_cost_schedules_sides_and_slippage_stress():
    model = CostModel(slippage_bps=5)
    base = model.cost(date=date(2025,1,1), side='BUY', turnover=1_000_000)
    assert base['stt'] == 1000 and base['stamp_duty'] == 150
    assert base['exchange'] == pytest.approx(29.7) and base['slippage'] == 500
    assert base['gst'] == pytest.approx(.18*(29.7+1+1))
    sell = model.cost(date=date(2025,1,1), side='SELL', turnover=1_000_000)
    assert sell['stamp_duty'] == 0 and sell['dp_charge'] == 13
    for multiplier in (1.5, 2):
        stress = CostModel(slippage_bps=5, slippage_multiplier=multiplier).cost(date=date(2025,1,1), side='BUY', turnover=1_000_000)
        assert stress['total']-base['total'] == pytest.approx(500*(multiplier-1))
    revised = model.cost(date=date(2026,3,1), side='BUY', turnover=1_000_000)
    assert revised['exchange'] == pytest.approx(30.699)
    assert revised['exchange']+revised['ipft'] == pytest.approx(base['exchange']+base['ipft'])
    with pytest.raises(ValueError, match='verified cost'):
        model.cost(date=date(2016,1,1), side='BUY', turnover=1000)
    assert not CostModel(allow_estimated_history=True).cost(date=date(2016,1,1), side='BUY', turnover=1000)['schedule_verified']


def test_constant_price_simulation_costs_reduce_nav():
    prices, _, sessions = market_fixture(stocks=2, days=65, start='2024-10-01')
    for name in ('adjusted_open','adjusted_close'):
        prices[name] = 100.
    scores = execution_scores(prices)
    base = run_backtest(prices, scores, sessions, cost_model=CostModel())
    stress = run_backtest(prices, scores, sessions, cost_model=CostModel(cost_multiplier=2))
    assert stress.equity_curve.nav.iloc[-1] < base.equity_curve.nav.iloc[-1] < 1_000_000


def test_walk_forward_labels_are_purged_and_embargoed():
    dates = pd.bdate_range('2010-01-01','2016-12-31')
    labels = pd.DataFrame(dict(as_of=dates, exit_date=pd.Series(dates).shift(-63), label_available=True))
    window = rolling_windows(first_test_year=2016,last_test_year=2016)[0]
    train = purged_training_labels(labels, window, dates)
    cutoff = dates[dates < pd.Timestamp('2016-01-01')][-64]
    assert train.exit_date.le(cutoff).all() and train.as_of.max() < pd.Timestamp('2016-01-01')


def test_overlapping_ic_uses_reproducible_block_bootstrap():
    values = np.sin(np.arange(400)/20)/10 + .02
    one = block_bootstrap(values, samples=100, seed=12)
    assert one == block_bootstrap(values, samples=100, seed=12)
    assert one['lower'] <= one['upper']
    assert block_bootstrap(values[:50])['status'] == 'INSUFFICIENT_INDEPENDENT_BLOCKS'


def test_diagnostics_keep_censored_tail_separate_from_missing_mature_labels():
    day = pd.Timestamp('2025-01-01')
    scores = pd.DataFrame(dict(as_of=[day]*20, instrument_id=[str(i) for i in range(20)], raw_score=np.arange(20)))
    labels = scores[['as_of','instrument_id']].copy()
    labels['entry_date'] = day+pd.Timedelta(days=1); labels['exit_date'] = day+pd.Timedelta(days=90)
    labels['stock_return_63'] = np.arange(20)/100; labels['benchmark_return_63'] = 0
    labels['excess_return_63'] = labels.stock_return_63; labels['label_available'] = True
    labels.loc[0,['exit_date','stock_return_63','excess_return_63']] = [pd.NaT,np.nan,np.nan]
    labels.loc[0,'label_available'] = False
    ic, deciles, summary = diagnostics(scores,labels)
    assert summary['label_coverage'] == 1 and summary['censored_tail_rows'] == 1
    assert summary['mean_IC'] == pytest.approx(1) and len(deciles) == 10
