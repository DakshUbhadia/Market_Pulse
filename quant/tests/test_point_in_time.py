from datetime import date
from pathlib import Path

import pandas as pd
import pytest
from defusedxml.common import DefusedXmlException

from quant.data.nse_client import RawResponse
from quant.data.nse_financials import parse_financial_filings, available_filings
from quant.data.nse_shareholding import parse_shareholding
from quant.data.xbrl import extract_financials, parse_xbrl
from quant.data.shareholding_xbrl import parse_shareholding_xbrl
from quant.data.rbi_macro import parse_macro, available_macro

RAW = RawResponse('https://www.nseindia.com/api/test', '2026-11-09T20:00:00+05:30',
                  'a' * 64, Path('raw.json'), 200)


def instance(facts='', contexts=''):
    return ('''<xbrl xmlns="http://www.xbrl.org/2003/instance" xmlns:f="urn:finance"
                xmlns:d="http://xbrl.org/2006/xbrldi">
        <context id="q"><entity><identifier scheme="ISIN">INE000000001</identifier></entity>
          <period><startDate>2024-04-01</startDate><endDate>2024-06-30</endDate></period></context>
        <unit id="INR"><measure>f:INR</measure></unit>''' + contexts + facts + '</xbrl>').encode()


def test_financial_facts_respect_period_and_schema():
    content = instance('<f:RevenueFromOperations contextRef="q" unitRef="INR">123</f:RevenueFromOperations>'
                       '<f:InterestEarned contextRef="q" unitRef="INR">42</f:InterestEarned>')
    assert extract_financials(content, '2024-06-30')['revenue'] == 123
    bank = extract_financials(content, '2024-06-30', bank=True)
    assert bank['interest_income'] == 42 and 'ebitda' not in bank
    assert extract_financials(content, '2024-09-30')['revenue'] is None
    assert extract_financials(content, '2024-06-30', consolidated=True)['revenue'] is None


def test_conflicting_quarter_and_ytd_are_not_selected_arbitrarily():
    context = '<context id="ytd"><period><startDate>2024-01-01</startDate><endDate>2024-06-30</endDate></period></context>'
    content = instance('<f:RevenueFromOperations contextRef="q" unitRef="INR">100</f:RevenueFromOperations>'
                       '<f:RevenueFromOperations contextRef="ytd" unitRef="INR">200</f:RevenueFromOperations>', context)
    assert extract_financials(content, '2024-06-30')['revenue'] is None
    assert extract_financials(content, '2024-06-30', period_start='2024-04-01')['revenue'] == 100


def test_xml_entity_expansion_is_rejected():
    with pytest.raises(ValueError, match='unsafe XBRL'):
        parse_xbrl(b'<!DOCTYPE x [<!ENTITY e "123">]><xbrl>&e;</xbrl>')


def test_filing_available_after_dissemination_and_revisions_preserved():
    record = dict(symbol='TEST', isin='INE000000001', toDate='30-Jun-2024',
                  consolidated='Non-Consolidated', broadCastDate='01-Aug-2024 16:00:00',
                  exchdisstime='01-Aug-2024 16:05:00', xbrl='https://nsearchives.nseindia.com/test.xml')
    frame = parse_financial_filings([record, dict(record, exchdisstime='02-Aug-2024 16:00:00')], RAW)
    assert frame.filing_id.is_unique
    assert available_filings(frame, '2024-08-01T16:04:00+05:30').empty
    assert len(available_filings(frame, '2024-08-01T16:06:00+05:30')) == 1
    unknown = parse_financial_filings([dict(record, exchdisstime=None)], RAW)
    assert available_filings(unknown, '2026-11-09T20:00:00+05:30').empty


def test_shareholding_preserves_versions_and_unknown_percentages():
    record = dict(symbol='TEST', date='30-Sep-2024', broadcastDate='15-Oct-2024 16:00:00')
    frame = parse_shareholding([record, dict(record, revisionDate='16-Oct-2024 16:00:00')], RAW)
    assert frame.version.is_unique and frame.promoter_pct.isna().all()


def test_revision_cannot_be_used_before_revision_broadcast():
    record = dict(symbol='TEST', isin='INE000000001', toDate='30-Jun-2024',
                  exchdisstime='01-Aug-2024 16:00:00', revisionDate='03-Aug-2024 16:00:00')
    frame = parse_financial_filings([record], RAW)
    assert available_filings(frame, '2024-08-02T20:00:00+05:30').empty
    assert len(available_filings(frame, '2024-08-03T20:00:00+05:30')) == 1
    original = dict(record, revisionDate=None)
    reversed_versions = parse_financial_filings([record, original], RAW)
    selected = available_filings(reversed_versions, '2024-08-03T20:00:00+05:30')
    assert selected.filing_id.iloc[0] == reversed_versions.filing_id.iloc[0]


def test_shareholding_context_percentage():
    xml = instance('<f:ShareholdingOfPromoterAndPromoterGroupAsPercentageOfTotalNumberOfShares contextRef="q">55</f:ShareholdingOfPromoterAndPromoterGroupAsPercentageOfTotalNumberOfShares>')
    assert parse_shareholding_xbrl(xml, '2024-06-30')['promoter_pct'] == 55
    with pytest.raises(ValueError):
        parse_shareholding_xbrl(xml.replace(b'>55<', b'>155<'), '2024-06-30')


def test_macro_filters_dimensions_and_never_invents_publication_dates():
    spec = dict(parser='sdmx', filters={'currency': 'USD'}, unit='INR_PER_USD', table='market/forex')
    content = b'time_period,currency,obs_value,unit_mult\n2024-06-30,USD,83.5,0\n2024-06-30,EUR,90,0\n'
    frame = parse_macro(content, 'usd_inr', spec, url='https://example.test', fetched_at=RAW.fetched_at)
    assert frame.value.iloc[0] == 83.5 and len(frame) == 1
    assert frame.publication_date.isna().all()
    assert available_macro(frame, '2024-07-01T20:00:00+05:30').empty
    with pytest.raises(ValueError, match='Duplicate'):
        parse_macro(content + b'2024-06-30,USD,84,0\n', 'usd_inr', spec,
                     url='https://example.test', fetched_at=RAW.fetched_at)
