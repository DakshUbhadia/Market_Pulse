import json
from datetime import date

import pytest

from quant.data.nifty_tri import parse_tri
from quant.backtest.benchmarks import total_return_index_returns
import pandas as pd


def test_official_tri_schema_and_legacy_envelope():
    payload = [{'Index Name':'Nifty 50','Date':'12 Nov 2026','TotalReturnsIndex':'38473.73'}]
    for content in (json.dumps(payload), json.dumps(dict(d=json.dumps(payload)))):
        result = parse_tri(content,'NIFTY 50',date(2026,11,1),date(2026,11,12))
        assert result.close.iloc[0] == 38473.73
        assert result.index_name.iloc[0] == 'NIFTY 50 TRI'


def test_tri_html_wrong_identity_duplicates_and_bad_prices_fail():
    for payload in ('<html>blocked</html>', '[]', json.dumps([
            {'Index Name':'Nifty 500','Date':'12 Nov 2026','TotalReturnsIndex':'1'}]),
            json.dumps([{'Index Name':'Nifty 50','Date':'12 Nov 2026','TotalReturnsIndex':'-1'}])):
        with pytest.raises(ValueError):
            parse_tri(payload,'NIFTY 50',date(2026,11,1),date(2026,11,12))


def test_tri_returns_require_prior_close_and_do_not_invent_open():
    dates = pd.bdate_range('2026-11-02',periods=4)
    frame = pd.DataFrame(dict(trade_date=dates,close=[100,101,102,103]))
    returns = total_return_index_returns(frame,dates[1:])
    assert returns.iloc[0] == pytest.approx(.01)
    with pytest.raises(ValueError,match='prior close'):
        total_return_index_returns(frame,dates)
    with pytest.raises(ValueError,match='Incomplete'):
        total_return_index_returns(frame.drop(index=2),dates[1:])
    with pytest.raises(ValueError,match='prior close'):
        total_return_index_returns(frame.drop(index=1),dates[2:],dates)
