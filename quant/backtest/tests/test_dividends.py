import pandas as pd
import pytest

from quant.backtest.corporate_actions import dividend_events, dividend_credits


def event(day):
    return pd.DataFrame([dict(event_id='dividend',instrument_id='a',ex_date=day,
        action_type='DIVIDEND',parse_status='PARSED',cash_amount=2.0)])


def test_dividend_credit_uses_split_adjusted_share_basis():
    day = pd.Timestamp('2025-01-01')
    events = dividend_events(event(day))[day]
    credits = dividend_credits(events,dict(a=20),dict(a=dict(raw_close=100,adjusted_close=50)),day)
    assert credits[0]['cash_credit'] == 20  # 10 raw shares x INR 2
    assert not dividend_credits(events,{},dict(a=dict(split_factor=1)),day)


def test_ambiguous_or_unverified_dividend_for_holding_stops_run():
    day = pd.Timestamp('2025-01-01')
    events = event(day)
    with pytest.raises(ValueError,match='share basis'):
        dividend_credits(events,dict(a=20),{},day)
    events['parse_status']='NEEDS_REVIEW'
    with pytest.raises(ValueError,match='Unverified'):
        dividend_credits(events,dict(a=20),dict(a=dict(split_factor=1)),day)


def test_ex_date_cash_offsets_price_drop_without_double_counting():
    from quant.backtest.engine import run_backtest
    from quant.backtest.portfolio import PortfolioConfig
    from quant.tests.research_fixtures import market_fixture, execution_scores
    from test_simulation import zero_cost
    prices,_,sessions = market_fixture(stocks=1,days=40,start='2024-10-01')
    ex_date = pd.Timestamp('2024-11-05')
    for key in ('adjusted_open','adjusted_close','raw_close'):
        prices[key] = 100.
        prices.loc[prices.trade_date >= ex_date,key] = 98.
    events = event(ex_date).assign(instrument_id='id-000')
    config = PortfolioConfig(holdings=1,max_weight=1,entry_percentile=0,exit_percentile=0)
    result = run_backtest(prices,execution_scores(prices),sessions,portfolio=config,
        cost_model=zero_cost(),corporate_actions=events)
    assert result.dividends.cash_credit.sum() == pytest.approx(20_000)
    assert result.equity_curve.nav.iloc[-1] == pytest.approx(1_000_000)
    assert result.equity_curve.dividend_cash.gt(0).sum() == 1


def test_buyer_on_ex_date_has_no_entitlement():
    from quant.backtest.engine import run_backtest
    from quant.tests.research_fixtures import market_fixture, execution_scores
    from test_simulation import zero_cost
    prices,_,sessions = market_fixture(stocks=1,days=40,start='2024-10-01')
    events = event(pd.Timestamp('2024-11-01')).assign(instrument_id='id-000')
    result = run_backtest(prices,execution_scores(prices),sessions,cost_model=zero_cost(),corporate_actions=events)
    assert result.dividends.empty


def test_ex_date_seller_retains_entitlement_and_executable_prices_are_unchanged():
    from quant.backtest.engine import run_backtest
    from quant.backtest.portfolio import PortfolioConfig
    from quant.tests.research_fixtures import market_fixture, execution_scores
    from quant.backtest.tests.test_simulation import zero_cost
    prices,_,sessions = market_fixture(stocks=1,days=65,start='2024-10-01')
    prices['adjusted_open'] = prices['adjusted_close'] = prices['raw_close'] = 100.
    original = prices.copy(deep=True)
    def target(selected,current,config):
        return pd.Series(dtype=float) if len(selected) and selected.as_of.iloc[0] >= pd.Timestamp('2024-11-29') else pd.Series({'id-000':1.})
    result = run_backtest(prices,execution_scores(prices),sessions,cost_model=zero_cost(),
        portfolio=PortfolioConfig(holdings=1,max_weight=1),target_builder=target,
        corporate_actions=event(pd.Timestamp('2024-12-02')).assign(instrument_id='id-000'))
    assert result.dividends.cash_credit.sum() == pytest.approx(20_000)
    assert result.trades.query("side == 'SELL'").trade_date.tolist() == [pd.Timestamp('2024-12-02')]
    assert result.dividends.trade_date.tolist() == [pd.Timestamp('2024-12-02')]
    pd.testing.assert_frame_equal(prices,original)
