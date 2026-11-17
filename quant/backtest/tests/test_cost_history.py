from datetime import date

import pytest

from quant.backtest.costs import CostModel, CostSchedule


def test_cost_schedule_before_gst():
    model = CostModel(slippage_bps=0,allow_estimated_history=True)
    for day, tax in [(date(2016,5,31),.145),(date(2016,6,1),.15),(date(2017,6,30),.15)]:
        result = model.cost(date=day,side='BUY',turnover=100000)
        base = sum(result[key] for key in ('brokerage','exchange','ipft','sebi','dp_charge'))
        assert result['service_tax'] == pytest.approx(tax*base)
        assert result['gst'] == 0
        assert result['cost_status'] == 'HISTORICAL_COST_PROXY'
        assert not result['schedule_verified']


def test_cost_schedule_after_gst():
    model = CostModel(slippage_bps=0,allow_estimated_history=True)
    result = model.cost(date=date(2017,7,1),side='SELL',turnover=100000)
    assert result['service_tax'] == 0
    assert result['gst'] == pytest.approx(.18*sum(result[key] for key in
        ('brokerage','exchange','ipft','sebi','dp_charge')))
    # STT and stamp duty are outside the taxable fee base.
    assert result['stt'] == 100


def test_cost_schedule_after_2020_stamp_change():
    model = CostModel(slippage_bps=0,allow_estimated_history=True)
    for side, expected in [('BUY',15),('SELL',0)]:
        assert model.cost(date=date(2020,7,1),side=side,turnover=100000)['stamp_duty'] == pytest.approx(expected)
    assert model.cost(date=date(2020,6,30),side='SELL',turnover=100000)['stamp_duty'] == pytest.approx(30)


def test_current_delivery_cost_and_exchange_eras():
    model = CostModel(slippage_bps=0,allow_estimated_history=True,market_impact_bps=2)
    assert model.schedule(date(2023,3,31)).exchange_rate == .0000345
    assert model.schedule(date(2023,4,1)).exchange_rate == .0000325
    assert model.schedule(date(2024,10,1)).exchange_rate == .0000297
    assert model.schedule(date(2026,3,1)).exchange_rate == .000030699
    result = model.cost(date=date(2026,11,12),side='SELL',turnover=100000)
    assert result['market_impact'] == 20
    assert result['schedule_verified'] and result['stamp_duty'] == 0
    assert result['dp_charge'] == 13
    rows = model.schedule_table()
    assert {'effective_from','effective_to','product','side','charge_type','rate_type','rate','source_reference','verified'} == set(rows[0])
    assert any(row['charge_type']=='market_impact' and not row['verified'] for row in rows)


def test_custom_proxy_cannot_bypass_opt_in_and_no_arbitrary_date_fallback():
    model = CostModel(schedules=(CostSchedule(date(2016,1,1),verified=False),))
    with pytest.raises(ValueError,match='opt-in'):
        model.cost(date=date(2020,1,1),side='BUY',turnover=1000)
    with pytest.raises(ValueError,match='supported research'):
        CostModel(allow_estimated_history=True).schedule(date(2010,1,1))
