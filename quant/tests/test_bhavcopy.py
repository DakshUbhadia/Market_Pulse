from datetime import date
from io import BytesIO
from zipfile import ZipFile, BadZipFile
from unittest.mock import Mock

import pandas as pd
import pytest
import requests

from quant.config import Config
from quant.data.http import Downloader
from quant.data.nse_bhavcopy import LEGACY, UDIFF, parse_bhavcopy, source_url
from quant.data.dhan_instruments import parse_instruments
from quant.storage.parquet_store import write_prices
from quant.storage.duckdb_store import query_prices
from quant.pipeline.bootstrap_history import run


def archive(day, mapping, **overrides):
    row = dict(trade_date=day.isoformat(), symbol='TEST', series='EQ', isin='INE000000001',
               open='100', high='110', low='90', close='105', last='104', previous_close='99',
               volume='1000', traded_value='104000', num_trades='100')
    row.update(overrides)
    csv = pd.DataFrame([{mapping[key]: value for key, value in row.items()}]).to_csv(index=False)
    buffer = BytesIO()
    with ZipFile(buffer, 'w') as zipped:
        zipped.writestr('bhav.csv', csv)
    return buffer.getvalue()


@pytest.mark.parametrize('day,mapping', [(date(2024, 7, 5), LEGACY), (date(2024, 7, 8), UDIFF)])
def test_normalization_and_storage(tmp_path, day, mapping):
    frame = parse_bhavcopy(archive(day, mapping), day)
    assert frame.close.iloc[0] == 105
    assert frame.volume.iloc[0] == 1000
    assert len(frame.source_hash.iloc[0]) == 64
    write_prices(frame, tmp_path)
    write_prices(frame, tmp_path)
    result = query_prices(tmp_path, start=day, end=day, symbol='TEST', series='EQ')
    assert len(result) == 1
    assert result.traded_value.iloc[0] == 104000
    assert query_prices(tmp_path, symbol="TEST' OR 1=1 --").empty


def test_era_schemas_match():
    old = parse_bhavcopy(archive(date(2024, 7, 5), LEGACY), date(2024, 7, 5))
    new = parse_bhavcopy(archive(date(2024, 7, 8), UDIFF), date(2024, 7, 8))
    assert old.dtypes.to_dict() == new.dtypes.to_dict()
    columns = [c for c in old if c not in ('trade_date', 'source_file', 'source_hash')]
    pd.testing.assert_frame_equal(old[columns], new[columns])


def test_query_across_optional_isin_schemas(tmp_path):
    old_day, new_day = date(2010, 1, 4), date(2024, 7, 8)
    old = parse_bhavcopy(archive(old_day, LEGACY), old_day)
    old['isin'] = None
    write_prices(old, tmp_path)
    write_prices(parse_bhavcopy(archive(new_day, UDIFF), new_day), tmp_path)
    assert len(query_prices(tmp_path)) == 2


@pytest.mark.parametrize('changes', [{'close': '-1'}, {'volume': '1.5'}, {'high': '99'},
                                    {'symbol': ''}, {'traded_value': 'inf'}, {'open': 'oops'},
                                    {'trade_date': '2024-07-09'}, {'num_trades': '-1'}])
def test_reject_bad_data(changes):
    day = date(2024, 7, 8)
    with pytest.raises(ValueError):
        parse_bhavcopy(archive(day, UDIFF, **changes), day)


def test_duplicate_keys_rejected(tmp_path):
    day = date(2024, 7, 8)
    frame = parse_bhavcopy(archive(day, UDIFF), day)
    with pytest.raises(ValueError, match='duplicate'):
        write_prices(pd.concat([frame, frame]), tmp_path)


def test_urls():
    assert 'cm05JUL2024bhav.csv.zip' in source_url(date(2024, 7, 5))
    assert '20240708_F_0000' in source_url(date(2024, 7, 8))


def test_optional_last_and_unknown_series_are_flagged():
    day = date(2024, 7, 8)
    frame = parse_bhavcopy(archive(day, UDIFF, last=''), day)
    assert pd.isna(frame['last'].iloc[0])
    assert frame.data_quality.iloc[0] == 'MISSING_LAST'
    frame = parse_bhavcopy(archive(day, UDIFF, series=''), day)
    assert frame.series.iloc[0] == ''
    assert frame.data_quality.iloc[0] == 'MISSING_SERIES'


def test_bad_archive_reported(tmp_path, monkeypatch):
    monkeypatch.setattr(Downloader, 'fetch', lambda *args: b'not a zip')
    day = date(2024, 7, 8)
    report = run(Config(data_dir=tmp_path), day, day, instruments=False)
    assert report['status'] == 'FAILED'
    assert not report['loaded']


def test_cache_checksum_and_url(tmp_path):
    session = Mock()
    session.get.return_value.content = b'valid csv'
    session.get.return_value.status_code = 200
    downloader = Downloader(Config(request_interval=0), session)
    path = tmp_path / 'file.csv'
    downloader.fetch('https://example.test/a', path)
    downloader.fetch('https://example.test/a', path)
    assert session.get.call_count == 1
    path.write_bytes(b'corrupt')
    downloader.fetch('https://example.test/a', path)
    assert session.get.call_count == 2
    downloader.fetch('https://example.test/b', path)
    assert session.get.call_count == 3


def test_no_retry_for_404(tmp_path):
    session = Mock()
    response = Mock(status_code=404)
    session.get.side_effect = requests.HTTPError(response=response)
    with pytest.raises(requests.HTTPError):
        Downloader(Config(request_interval=0), session).fetch('https://example.test/a', tmp_path / 'a')
    assert session.get.call_count == 1


def test_retry_transient_failure(tmp_path, monkeypatch):
    monkeypatch.setattr('quant.data.http.time.sleep', lambda _: None)
    session = Mock()
    response = Mock(content=b'csv', status_code=200)
    session.get.side_effect = [requests.Timeout(), response]
    assert Downloader(Config(request_interval=0), session).fetch('https://example.test/a', tmp_path / 'a') == b'csv'
    assert session.get.call_count == 2


def test_dhan_identity():
    csv = ('EXCH_ID,SEGMENT,SECURITY_ID,ISIN,SYMBOL_NAME,UNDERLYING_SYMBOL,SERIES,INSTRUMENT\n'
           'NSE,E,123,INE000000001,Test Company,TEST,EQ,EQUITY\n'
           'BSE,E,500001,INE000000001,Test Company,TESTB,A,EQUITY\n'
           'NSE,D,999,INE000000001,Test Future,TESTFUT,,FUTSTK\n').encode()
    first = parse_instruments(csv)
    renamed = parse_instruments(csv.replace(b'TEST,', b'RENAMED,'))
    assert len(first) == 1
    assert first.instrument_id.iloc[0] == renamed.instrument_id.iloc[0]
    assert first.bse_scrip_code.iloc[0] == '500001'
    assert first.nse_symbol.iloc[0] == 'TEST'


def test_backfill_missing_date_is_not_holiday(tmp_path, monkeypatch):
    response = Mock(status_code=404)
    monkeypatch.setattr(Downloader, 'fetch', Mock(side_effect=requests.HTTPError(response=response)))
    day = date(2024, 7, 6)
    report = run(Config(data_dir=tmp_path), day, day, instruments=False)
    assert report['status'] == 'INCOMPLETE'
    assert report['coverage'] is None
    assert len(report['unresolved']) == 1


def test_verified_calendar_coverage(tmp_path, monkeypatch):
    day = date(2024, 7, 8)
    monkeypatch.setattr(Downloader, 'fetch', lambda *args: archive(day, UDIFF))
    report = run(Config(data_dir=tmp_path), day, day, instruments=False, expected_dates={day})
    assert report['status'] == 'SUCCESS'
    assert report['coverage'] == 1
