"""Explicit official TRI schema smoke test, separate from synthetic unit tests."""
from datetime import date

import pytest
import requests

from quant.data.nifty_tri import SOURCE_URL, SOURCE_PAGE, parse_tri

pytestmark = pytest.mark.integration


@pytest.mark.parametrize('name',['NIFTY 50','NIFTY 500'])
def test_official_tri_live_source(name):
    response = requests.post(SOURCE_URL,json=dict(cinfo=str(dict(name=name,
        startDate='08-Jul-2024',endDate='09-Jul-2024',indexName=name))),
        headers={'User-Agent':'Mozilla/5.0','Referer':SOURCE_PAGE},timeout=30)
    response.raise_for_status()
    frame = parse_tri(response.content,name,date(2024,7,8),date(2024,7,9))
    assert set(frame.trade_date.dt.date)=={date(2024,7,8),date(2024,7,9)}
