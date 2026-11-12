import pandas as pd

from quant.universe.eligible import build_eligible_universe
from quant.tests.research_fixtures import market_fixture


def test_ipo_liquidity_and_unresolved_action_eligibility():
    prices, _, sessions = market_fixture(stocks=4)
    prices = prices[~((prices.instrument_id == 'id-001') & (prices.trade_date < sessions[100]))].copy()
    prices.loc[prices.instrument_id == 'id-002', 'traded_value'] = 1000
    prices.loc[(prices.instrument_id == 'id-003') & (prices.trade_date >= sessions[-1]), 'adjustment_status'] = 'NEEDS_REVIEW'
    result = build_eligible_universe(prices, sessions, as_of=sessions[-1]).set_index('instrument_id')
    assert result.loc['id-000', 'eligible']
    assert result.loc['id-001', 'exclusion_reason'] == 'INSUFFICIENT_HISTORY'
    assert result.loc['id-002', 'exclusion_reason'] == 'LOW_LIQUIDITY'
    assert result.loc['id-003', 'exclusion_reason'] == 'CORPORATE_ACTION_UNRESOLVED'


def test_historical_delisted_and_renamed_stock_keeps_identity():
    prices, _, sessions = market_fixture(stocks=2)
    prices = prices[~((prices.instrument_id == 'id-001') & (prices.trade_date > sessions[280]))].copy()
    prices.loc[(prices.instrument_id == 'id-000') & (prices.trade_date >= sessions[270]), 'symbol'] = 'RENAMED'
    old = build_eligible_universe(prices, sessions, as_of=sessions[260])
    assert set(old.instrument_id) == {'id-000', 'id-001'} and old.eligible.all()
    current = build_eligible_universe(prices, sessions, as_of=sessions[-1])
    assert current.instrument_id.tolist() == ['id-000']
    assert current.symbol.tolist() == ['RENAMED']


def test_missing_sessions_do_not_compress_history_or_presence():
    prices, _, sessions = market_fixture(stocks=1)
    prices = prices[~prices.trade_date.isin(sessions[-30:-1])]
    result = build_eligible_universe(prices, sessions, as_of=sessions[-1]).iloc[0]
    assert result.history_sessions == len(sessions)
    assert result.exclusion_reason == 'INSUFFICIENT_TRADING_PRESENCE'
