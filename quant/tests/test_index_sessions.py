from datetime import date

import pytest

from quant.data.nse_index_sessions import parse_index_sessions
from quant.data.nse_client import NseSourceError
from test_calendar import raw


def payload(day='06-Feb-2010', **changes):
    row = dict(EOD_TIMESTAMP=day, EOD_INDEX_NAME='S&P CNX NIFTY', EOD_OPEN_INDEX_VAL=100,
               EOD_HIGH_INDEX_VAL=110, EOD_LOW_INDEX_VAL=90, EOD_CLOSE_INDEX_VAL=105)
    row.update(changes)
    return {'data': [row]}


def test_official_index_proves_special_weekend_session():
    sessions = parse_index_sessions(payload(), date(2010, 2, 1), date(2010, 2, 28), raw())
    assert date(2010, 2, 6) in sessions
    assert date(2010, 2, 7) not in sessions  # No conclusion about this date's holiday status.


@pytest.mark.parametrize('data', [payload(day='06-Mar-2010'), payload(EOD_INDEX_NAME='OTHER'),
                                payload(EOD_HIGH_INDEX_VAL=99), {'data': []}])
def test_index_session_evidence_rejects_wrong_range_name_or_prices(data):
    with pytest.raises((NseSourceError, ValueError)):
        parse_index_sessions(data, date(2010, 2, 1), date(2010, 2, 28), raw())
