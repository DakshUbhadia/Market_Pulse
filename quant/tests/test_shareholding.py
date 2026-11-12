import pytest

from quant.data.shareholding_xbrl import parse_shareholding_xbrl
from quant.data.nse_shareholding import parse_shareholding, available_shareholding
from test_point_in_time import instance, RAW


def test_dimensional_aggregate_fraction_is_percentage():
    context = '''<context id="promoter"><entity><segment>
      <d:explicitMember dimension="f:CategoryOfShareholdersAxis">f:ShareholdingOfPromoterAndPromoterGroupMember</d:explicitMember>
      </segment></entity><period><instant>2024-06-30</instant></period></context>'''
    content = instance('<f:ShareholdingAsAPercentageOfTotalNumberOfShares contextRef="promoter">0.55</f:ShareholdingAsAPercentageOfTotalNumberOfShares>', context)
    assert parse_shareholding_xbrl(content, '2024-06-30')['promoter_pct'] == pytest.approx(55)
    assert parse_shareholding_xbrl(content, '2024-09-30')['promoter_pct'] is None


def test_revised_shareholding_has_own_availability_time():
    record = dict(symbol='TEST', date='30-Jun-2024', broadcastDate='01-Aug-2024 16:00:00',
                  revisionDate='03-Aug-2024 16:00:00')
    frame = parse_shareholding([record], RAW)
    assert available_shareholding(frame, '2024-08-02T20:00:00+05:30').empty
    assert len(available_shareholding(frame, '2024-08-03T20:00:00+05:30')) == 1
