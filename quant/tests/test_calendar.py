import json
from datetime import date
from pathlib import Path
from unittest.mock import Mock

import pandas as pd
import pytest

from quant.config import Config
from quant.data.nse_calendar import (build_calendar, calendar_report, loaded_bhavcopy_evidence,
                                    parse_holidays, parse_muhurat_notice)
from quant.data.nse_client import NseClient, NseSourceError, RawResponse
from quant.pipeline.update_calendar import refresh_calendar, read_calendar, reconcile_calendar
from quant.pipeline import bootstrap_history
from quant.storage.parquet_store import write_prices
from quant.data.nse_bhavcopy import parse_bhavcopy, UDIFF
from test_bhavcopy import archive

ASOF = '2026-11-09T18:00:00+05:30'


def test_historical_circular_requires_correct_year_and_reference():
    from quant.data.nse_calendar import parse_holiday_circular_text
    text = ('CAPITAL MARKET SEGMENT\nTrading holidays for the calendar year 2010\nDownload No.: 13713\n'
            + '\n'.join(f'{day} {day:02d}-Jan-10 Friday Holiday' for day in range(1, 10))
            + '\n10 26-Jan-10 Tuesday Republic Day\n11 05-Nov-10 Friday Laxmi Puja*\n'
            + '*Muhurat Trading will be conducted.')
    events = parse_holiday_circular_text(text, 2010, raw(), '13713')
    assert not events[date(2010, 1, 26)]['is_trading_session']
    assert events[date(2010, 11, 5)]['session_type'] == 'MUHURAT'
    with pytest.raises(NseSourceError):
        parse_holiday_circular_text(text, 2011, raw(), '13713')
    with pytest.raises(NseSourceError):
        parse_holiday_circular_text(text, 2010, raw(), 'wrong')


def raw():
    return RawResponse('https://www.nseindia.com/api/holiday-master?type=trading&year=2024',
                       ASOF, 'a' * 64, Path('raw.json'), 200)


def holidays():
    return {'CM': [
        {'tradingDate': '26-Jan-2024', 'description': 'Republic Day'},
        {'tradingDate': '02-Mar-2024', 'description': 'Special Live Trading'},
        {'tradingDate': '01-Nov-2024', 'description': 'Diwali Laxmi Pujan*'},
    ]}


def calendar(start=date(2024, 1, 1), end=date(2024, 12, 31), **kwargs):
    return build_calendar(start, end, {2024: parse_holidays(holidays(), 2024, raw())},
                          {2024: raw()}, normalized_at=ASOF, **kwargs)


def test_weekend_holiday_special_and_sorted_unique_dates():
    frame = calendar().set_index('trade_date')
    assert not frame.loc['2024-01-06', 'is_trading_session']
    assert not frame.loc['2024-01-26', 'is_trading_session']
    assert frame.loc['2024-03-02', 'is_trading_session']
    assert frame.loc['2024-03-02', 'session_type'] == 'SPECIAL'
    assert frame.index.is_unique and frame.index.is_monotonic_increasing
    assert len(frame) == 366
    assert not frame.verified.any()  # Expected schedule is not observed price coverage.


@pytest.mark.parametrize('payload', [{}, {'FO': []}, {'CM': []},
                                   {'CM': [{'tradingDate': '26-Jan-2025', 'description': 'Holiday'}]},
                                   {'CM': [{'tradingDate': 'invalid', 'description': 'Holiday'}]}])
def test_no_silent_fallback_for_missing_or_wrong_year(payload):
    with pytest.raises(NseSourceError):
        parse_holidays(payload, 2024, raw())


def test_conflicting_duplicate_dates_fail():
    payload = holidays()
    payload['CM'].append({'tradingDate': '26-Jan-2024', 'description': 'Special Live Trading'})
    with pytest.raises(NseSourceError, match='Conflicting'):
        parse_holidays(payload, 2024, raw())


def test_diwali_holiday_is_not_automatically_a_session():
    row = calendar().set_index('trade_date').loc['2024-11-01']
    assert not row.is_trading_session
    assert row.needs_investigation
    assert row.investigation_reason == 'MUHURAT_REQUIRES_CONFIRMATION'


def test_explicit_muhurat_notice_overrides_holiday():
    body = b'<p>Muhurat Trading will be conducted on Friday, <b>November 01, 2024</b> on account of Diwali.</p>'
    specials = parse_muhurat_notice(body, raw())
    row = calendar(special_events=specials).set_index('trade_date').loc['2024-11-01']
    assert row.is_trading_session and row.session_type == 'MUHURAT'
    assert not row.needs_investigation


def test_unexpected_bhavcopy_becomes_verified_and_is_flagged():
    observations = {date(2024, 1, 20): {'source_url': 'https://nsearchives.nseindia.com/actual.zip',
                                       'raw_sha256': 'b' * 64}}
    frame = calendar(observed=observations)
    row = frame.set_index('trade_date').loc['2024-01-20']
    assert row.is_trading_session and row.verified and row.needs_investigation
    assert row.observed_raw_sha256 == 'b' * 64 and row.calendar_raw_sha256 == 'a' * 64
    assert calendar_report(frame)['verified_price_sessions'] == 1


def test_bhavcopy_resolves_ambiguous_muhurat_without_manual_input(tmp_path, monkeypatch):
    config = Config(data_dir=tmp_path)
    day = date(2024, 11, 1)
    monkeypatch.setattr('quant.data.http.Downloader.fetch', lambda *args: archive(day, UDIFF))
    frame, report = refresh_calendar(config, day, day, client=fake_client())
    row = frame.iloc[0]
    assert row.is_trading_session and row.verified and row.session_type == 'MUHURAT'
    assert not row.needs_investigation
    assert report['status'] == 'READY'
    assert config.calendar_text_path.read_text() == '2024-11-01\n'


def test_no_missing_years():
    with pytest.raises(ValueError, match='all requested years'):
        build_calendar(date(2023, 12, 1), date(2024, 1, 1), {2024: {}}, {2024: raw()}, normalized_at=ASOF)


def test_partition_contents_are_checked(tmp_path):
    config = Config(data_dir=tmp_path)
    day = date(2024, 7, 8)
    frame = parse_bhavcopy(archive(day, UDIFF), day)
    paths = write_prices(frame, config.prices_dir)
    observed, invalid = loaded_bhavcopy_evidence(config, day, day)
    assert day in observed and not invalid
    paths[0].write_bytes(b'not parquet')
    observed, invalid = loaded_bhavcopy_evidence(config, day, day)
    assert not observed and len(invalid) == 1


def fake_client():
    client = Mock()
    client.last_response = raw()
    def get_json(path, params=None, **kwargs):
        if 'indicesHistory' not in path:
            return holidays()
        day = pd.to_datetime(params['from'], dayfirst=True)
        while day.weekday() > 4:
            day += pd.Timedelta(days=1)
        return {'data': [{'EOD_TIMESTAMP': day.strftime('%d-%b-%Y'), 'EOD_INDEX_NAME': 'NIFTY 50',
                          'EOD_OPEN_INDEX_VAL': 100, 'EOD_HIGH_INDEX_VAL': 110,
                          'EOD_LOW_INDEX_VAL': 90, 'EOD_CLOSE_INDEX_VAL': 105}]}
    client.get_json.side_effect = get_json
    client.get_bytes.return_value = b'<p>No special dated notices.</p>'
    return client


def test_refresh_exports_calendar_and_preserves_prior_on_failure(tmp_path):
    config = Config(data_dir=tmp_path)
    frame, report = refresh_calendar(config, date(2024, 7, 5), date(2024, 7, 8), client=fake_client())
    assert report['expected_sessions'] == 2
    assert report['verified_price_sessions'] == 0
    assert config.calendar_text_path.read_text() == '2024-07-05\n2024-07-08\n'
    assert len(read_calendar(config, date(2024, 7, 5), date(2024, 7, 8))) == 4
    previous = config.calendar_path.read_bytes()
    failed = fake_client()
    failed.get_json.side_effect = NseSourceError('HTTP 403')
    with pytest.raises(NseSourceError):
        refresh_calendar(config, date(2024, 7, 5), date(2024, 7, 8), client=failed)
    assert config.calendar_path.read_bytes() == previous
    health = json.loads((tmp_path / 'reports/calendar-health.json').read_text())
    assert health['status'] == 'FAILED' and health['prior_calendar_retained']
    with pytest.raises(ValueError, match='refresh failed'):
        read_calendar(config, date(2024, 7, 5), date(2024, 7, 8))


def test_short_refresh_preserves_earlier_coverage(tmp_path):
    config = Config(data_dir=tmp_path)
    refresh_calendar(config, date(2024, 7, 5), date(2024, 7, 8), client=fake_client())
    frame, _ = refresh_calendar(config, date(2024, 7, 8), date(2024, 7, 9), client=fake_client())
    assert frame.trade_date.min().date() == date(2024, 7, 5)
    assert frame.trade_date.max().date() == date(2024, 7, 9)


def test_bootstrap_uses_generated_calendar_without_weekend_requests(tmp_path, monkeypatch):
    config = Config(data_dir=tmp_path)
    refresh_calendar(config, date(2024, 7, 5), date(2024, 7, 8), client=fake_client())
    calls = []
    from quant.data.nse_bhavcopy import LEGACY
    def fetch(self, url, path):
        calls.append(url)
        day = date(2024, 7, 5) if '05JUL' in url else date(2024, 7, 8)
        return archive(day, LEGACY if day.day == 5 else UDIFF)
    monkeypatch.setattr('quant.data.http.Downloader.fetch', fetch)
    monkeypatch.setattr('sys.argv', ['bootstrap_history', '--from', '2024-07-05', '--to', '2024-07-08',
                                    '--data-dir', str(tmp_path), '--calendar', 'cached', '--skip-instruments'])
    assert bootstrap_history.main() == 0
    assert len(calls) == 2
    assert bootstrap_history.main() == 0  # Restart uses validated partitions.
    assert len(calls) == 2
    report = reconcile_calendar(config, date(2024, 7, 5), date(2024, 7, 8))
    assert report['observed_price_coverage'] == 1


def test_reconciliation_revokes_verification_for_corrupt_partition(tmp_path, monkeypatch):
    config = Config(data_dir=tmp_path)
    day = date(2024, 7, 8)
    paths = write_prices(parse_bhavcopy(archive(day, UDIFF), day), config.prices_dir)
    refresh_calendar(config, day, day, client=fake_client())
    paths[0].write_bytes(b'broken')
    report = reconcile_calendar(config, day, day)
    assert report['verified_price_sessions'] == 0
    assert report['status'] == 'NEEDS_REVIEW'
    frame = pd.read_parquet(config.calendar_path)
    assert not frame.verified.iloc[0]
    assert pd.isna(frame.observed_raw_sha256.iloc[0])


def test_no_requests_for_holiday_only_range(tmp_path, monkeypatch):
    fetch = Mock()
    monkeypatch.setattr('quant.data.http.Downloader.fetch', fetch)
    report = bootstrap_history.run(Config(data_dir=tmp_path), date(2024, 1, 26), date(2024, 1, 26),
                                   instruments=False, expected_dates=set())
    assert report['status'] == 'SUCCESS'
    assert report['expected_sessions'] == 0
    assert report['coverage'] is None
    fetch.assert_not_called()


def test_access_block_stops_backfill_without_inflating_coverage(tmp_path, monkeypatch):
    import requests
    response = requests.Response()
    response.status_code = 403
    fetch = Mock(side_effect=requests.HTTPError(response=response))
    monkeypatch.setattr('quant.data.http.Downloader.fetch', fetch)
    days = {date(2024, 7, 8), date(2024, 7, 9)}
    report = bootstrap_history.run(Config(data_dir=tmp_path), min(days), max(days),
                                   instruments=False, expected_dates=days)
    assert report['status'] == 'FAILED'
    assert report['expected_sessions'] == 2 and report['coverage'] == 0
    assert report['unattempted_sessions'] == ['2024-07-09']
    assert fetch.call_count == 1


@pytest.mark.integration
def test_live_calendar(tmp_path):
    config = Config(data_dir=tmp_path)
    with NseClient(config) as client:
        for year in (2018, 2024, 2026):
            data = client.get_json('/api/holiday-master', params={'type': 'trading', 'year': year}, dataset='calendar')
            entries = parse_holidays(data, year, client.last_response)
            assert date(year, 1, 26) in entries
            assert not entries[date(year, 1, 26)]['is_trading_session']
        content = client.get_bytes('/resources/exchange-communication-holidays', dataset='calendar', suffix='html')
        assert parse_muhurat_notice(content, client.last_response)
