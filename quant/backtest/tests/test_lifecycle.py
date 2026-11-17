from datetime import date

import pandas as pd
import pytest

from quant.backtest.engine import run_backtest
from quant.backtest.lifecycle import Lifecycle, simulation_time
from quant.backtest.portfolio import PortfolioConfig
from quant.data.lifecycle_normalize import normalize_events
from quant.tests.research_fixtures import market_fixture, execution_scores
from quant.backtest.tests.test_simulation import zero_cost


def event(kind='SUSPENDED', announced='2024-11-04T17:00:00+05:30', effective='2024-11-08', **extra):
    return dict(instrument_id='id-000', symbol='STOCK000', isin='INE000A01000',
        event_type=kind,announced_at=announced,effective_date=effective,
        source_exchange='NSE',source_url='https://nsearchives.nseindia.com/test.pdf',
        source_sha256='a'*64,raw_path='raw/test.pdf',verification_status='VERIFIED',
        first_seen_at='2026-11-17T00:00:00Z',**extra)


def simulate(events, *, absent=None, scenario='KNOWN_EVENT_NEXT_OPEN_EXIT', successor=False):
    prices,_,sessions = market_fixture(stocks=2 if successor else 1, days=40,start='2024-10-01')
    prices['adjusted_open'] = prices['adjusted_close'] = prices['raw_close'] = 100.
    scores = execution_scores(prices[prices.instrument_id.eq('id-000')])
    if absent:
        prices = prices[~(prices.instrument_id.eq('id-000') & prices.trade_date.ge(absent))]
    return run_backtest(prices,scores,sessions,cost_model=zero_cost(),
        portfolio=PortfolioConfig(holdings=1,max_weight=1,entry_percentile=0,exit_percentile=0),
        lifecycle_events=normalize_events(events),lifecycle_scenario=scenario)


def test_known_future_suspension_blocks_new_entry():
    result = simulate([event(announced='2024-10-30T12:00:00+05:30')])
    assert result.trades.empty


def test_known_suspension_exits_at_next_executable_open():
    result = simulate([event()])
    sell = result.trades.query("side == 'SELL'").iloc[0]
    assert sell.trade_date == pd.Timestamp('2024-11-05')
    assert sell.exit_reason == 'KNOWN_LIFECYCLE_RISK'
    assert result.equity_curve.nav.iloc[-1] == pytest.approx(1_000_000)


def test_unexpected_suspension_does_not_invent_fill():
    with pytest.raises(ValueError,match='Unvalued holding'):
        simulate([event(announced='2024-11-08T08:00:00+05:30')],absent='2024-11-08')


def test_mandatory_cash_settlement_credits_on_documented_date():
    result = simulate([event('CASH_SETTLEMENT',mandatory=True,settlement_date='2024-11-08',
        cash_per_raw_share=120)],absent='2024-11-08',scenario='MANDATORY_ONLY')
    assert result.lifecycle.cash_credit.tolist() == pytest.approx([1_200_000])
    assert result.lifecycle.trade_date.tolist() == [pd.Timestamp('2024-11-08')]
    assert result.equity_curve.nav.iloc[-1] == pytest.approx(1_200_000)


def test_optional_tender_is_not_assumed():
    with pytest.raises(ValueError,match='Unvalued holding'):
        simulate([event('EXIT_OFFER',optional=True,offer_price=120,offer_start='2024-11-08',
            offer_end='2024-12-31')],absent='2024-11-08',scenario='MANDATORY_ONLY')


def test_merger_converts_to_successor_identity():
    result = simulate([event('SHARE_CONVERSION',mandatory=True,conversion_ratio=2,
        successor_instrument_id='id-001')],absent='2024-11-08',scenario='MANDATORY_ONLY',successor=True)
    final = result.holdings[result.holdings.trade_date.eq(result.holdings.trade_date.max())]
    assert final.instrument_id.tolist() == ['id-001']
    assert final.quantity.iloc[0] == pytest.approx(20_000)
    assert result.equity_curve.nav.iloc[-1] == pytest.approx(2_000_000)


def test_future_lifecycle_event_cannot_affect_past_signal():
    policy = Lifecycle(normalize_events([event()]))
    assert policy.status('id-000',simulation_time('2024-11-04','15:30'))['entry_allowed']
    assert not policy.status('id-000',simulation_time('2024-11-05','09:15'))['entry_allowed']


def test_relisting_does_not_retroactively_change_old_state():
    policy = Lifecycle(normalize_events([event(),event('RELISTING',
        announced='2024-11-11T12:00:00+05:30',effective='2024-11-14')]))
    assert not policy.status('id-000',simulation_time('2024-11-12','15:30'))['entry_allowed']
    assert policy.status('id-000',simulation_time('2024-11-14','15:30'))['entry_allowed']
    assert not policy.status('id-000',simulation_time('2024-11-08','15:30'))['entry_allowed']


def test_future_settlement_cannot_bridge_unvalued_sessions():
    with pytest.raises(ValueError,match='Unvalued holding'):
        simulate([event('CASH_SETTLEMENT',mandatory=True,settlement_date='2024-11-12',
            cash_per_raw_share=120)],absent='2024-11-08',scenario='MANDATORY_ONLY')


def test_offer_cannot_restore_suspended_trading_access():
    policy = Lifecycle(normalize_events([event(),event('EXIT_OFFER',
        announced='2024-11-09T12:00:00+05:30',effective='2024-11-10',optional=True)]))
    assert policy.status('id-000',simulation_time('2024-11-11','09:15'))['lifecycle_status'] == 'SUSPENDED'


def test_verified_events_require_publication_time():
    record = event()
    record['announced_at'] = None
    with pytest.raises(ValueError,match='timing'):
        normalize_events([record])


def test_unverified_current_list_cannot_infer_historical_timing():
    record = event()
    record.update(announced_at=None,verification_status='NEEDS_REVIEW')
    policy = Lifecycle(normalize_events([record]))
    assert policy.status('id-000',simulation_time('2024-11-11','09:15'))['entry_allowed']


def test_unsubstantiated_scenarios_are_rejected():
    with pytest.raises(ValueError,match='Unsupported'):
        Lifecycle(scenario='CONSERVATIVE_ZERO_RECOVERY')


def test_essaroil_official_exit_letter_cannot_create_earlier_knowledge_or_cash():
    import json
    from pathlib import Path
    record = json.loads((Path(__file__).parent/'fixtures/essaroil_exit_offer.json').read_text())
    policy = Lifecycle(normalize_events([record]))
    identity = record['instrument_id']
    assert policy.known(identity,simulation_time('2016-02-10','09:15')).empty
    assert not policy.resolutions(identity,simulation_time('2016-02-17','09:15'),set())
    assert record['last_trading_date'] < record['suspension_date'] < record['offer_start']
    assert record['offer_price'] == 262.8 and record['optional'] and not record['mandatory']


def test_mandatory_cash_uses_split_adjusted_units_once():
    from quant.backtest.lifecycle import share_factor
    assert 200 * share_factor(dict(raw_close=100,adjusted_close=50)) * 12 == 1200


def test_notice_published_after_open_waits_for_next_session():
    result = simulate([event(announced='2024-11-05T09:16:00+05:30')])
    assert result.trades.query("side == 'SELL'").trade_date.tolist() == [pd.Timestamp('2024-11-06')]


def test_essaroil_original_notice_exits_existing_holding_without_assuming_tender():
    import json
    from pathlib import Path
    from dataclasses import replace
    from quant.backtest.costs import CostModel
    record = json.loads((Path(__file__).parent/'fixtures/essaroil_suspension.json').read_text())
    prices,_,sessions = market_fixture(stocks=1,days=65,start='2015-12-01')
    scores = execution_scores(prices)
    scores['instrument_id'] = record['instrument_id']
    prices['instrument_id'] = record['instrument_id']
    prices['adjusted_open'] = prices['adjusted_close'] = prices['raw_close'] = 100.
    prices = prices[prices.trade_date < '2016-02-10']
    costs = CostModel(slippage_bps=0,schedules=(replace(zero_cost().schedules[0],effective_from=date(2015,1,1)),))
    result = run_backtest(prices,scores,sessions,cost_model=costs,lifecycle_events=normalize_events([record]),
        lifecycle_scenario='KNOWN_EVENT_NEXT_OPEN_EXIT',
        portfolio=PortfolioConfig(holdings=1,max_weight=1,entry_percentile=0,exit_percentile=0))
    sales = result.trades.query("side == 'SELL'")
    assert sales.trade_date.tolist() == [pd.Timestamp('2016-01-28')]
    assert sales.exit_reason.tolist() == ['KNOWN_LIFECYCLE_RISK']
    assert result.lifecycle.empty  # No tender or automatic settlement.
    assert result.equity_curve.nav.iloc[-1] == pytest.approx(1_000_000)
