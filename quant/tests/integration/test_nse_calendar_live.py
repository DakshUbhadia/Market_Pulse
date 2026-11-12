from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from quant.config import Config
from quant.data.nse_calendar import parse_holidays
from quant.data.nse_client import NseClient
from quant.data.nse_index_sessions import parse_index_sessions, PATH
from datetime import date

pytestmark = pytest.mark.integration


def test_live_calendar(tmp_path):
    config = Config(data_dir=tmp_path, retries=0, timeout=20)
    year = datetime.now(ZoneInfo(config.timezone)).year
    with NseClient(config) as client:
        payload = client.get_json('/api/holiday-master', params={'type': 'trading', 'year': year},
                                  dataset='calendar')
        events = parse_holidays(payload, year, client.last_response)
        assert len(events) >= 5


def test_live_independent_special_session_evidence(tmp_path):
    config = Config(data_dir=tmp_path, retries=0, timeout=20)
    with NseClient(config) as client:
        payload = client.get_json(PATH, params={'indexType': 'NIFTY 50', 'from': '01-02-2010',
                                                'to': '28-02-2010'}, dataset='calendar')
        events = parse_index_sessions(payload, date(2010, 2, 1), date(2010, 2, 28), client.last_response)
        assert date(2010, 2, 6) in events
