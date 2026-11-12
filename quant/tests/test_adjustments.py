import pandas as pd
import pytest

from quant.data.nse_corporate_actions import parse_subject
from quant.features.adjustments import adjust_prices
from quant.features.returns import calculate_returns


def prices(closes=(2000, 1000)):
    return pd.DataFrame(dict(trade_date=pd.to_datetime(['2024-01-01', '2024-01-02']),
                             symbol=['TEST'] * 2, series=['EQ'] * 2,
                             instrument_id=['id'] * 2, close=closes))


def actions(kind='SPLIT', **kwargs):
    row = dict(event_id='event', instrument_id='id', symbol='TEST', action_type=kind,
               ex_date=pd.Timestamp('2024-01-02'), ratio_numerator=2, ratio_denominator=1,
               cash_amount=None, parse_status='PARSED')
    row.update(kwargs)
    return pd.DataFrame([row])


@pytest.mark.parametrize('action', [actions(), actions('BONUS', ratio_numerator=1)])
def test_split_and_bonus_remove_artificial_crash(action):
    raw = prices()
    before = raw.copy(deep=True)
    result = calculate_returns(adjust_prices(raw, action))
    assert result.raw_return.iloc[-1] == -.5
    assert result.adjusted_return.iloc[-1] == pytest.approx(0)
    pd.testing.assert_frame_equal(raw, before)


def test_dividend_total_return_and_unresolved_action():
    result = calculate_returns(adjust_prices(prices((100, 95)), actions('DIVIDEND', cash_amount=5)))
    assert result.adjusted_return.iloc[-1] == pytest.approx(-.05)
    assert result.total_return.iloc[-1] == pytest.approx(0)
    excluded = adjust_prices(prices(), actions(parse_status='NEEDS_REVIEW'))
    assert excluded.adjusted_close.iloc[0] == 2000  # Future uncertainty cannot exclude an earlier observation.
    assert pd.isna(excluded.adjusted_close.iloc[1])


def test_dividend_total_return_includes_real_price_change():
    result = calculate_returns(adjust_prices(prices((100, 98)), actions('DIVIDEND', cash_amount=5)))
    assert result.total_return.iloc[-1] == pytest.approx(.03)  # (98 + 5) / 100 - 1


def test_symbol_reuse_does_not_link_different_instruments():
    raw = prices()
    raw.loc[1, 'instrument_id'] = 'different-company'
    result = calculate_returns(adjust_prices(raw, pd.DataFrame()))
    assert result.adjusted_return.isna().all()


def test_parser_is_conservative():
    assert parse_subject('Face Value Split From Rs 10/- Per Share To Rs 5/- Per Share')['ratio_numerator'] == 10
    assert parse_subject('Bonus 1:1')['parse_status'] == 'PARSED'
    assert parse_subject('Dividend - Rs 5 Per Share')['cash_amount'] == 5
    assert parse_subject('Bonus and Dividend')['parse_status'] == 'NEEDS_REVIEW'
    assert parse_subject('Rights 1:4')['parse_status'] == 'NEEDS_REVIEW'
