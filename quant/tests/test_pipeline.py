from datetime import date, datetime
from zoneinfo import ZoneInfo

import pytest

from quant.config import Config
from quant.pipeline.state import PipelineState
from quant.pipeline.cli import completed_day
from quant.pipeline.validate_data import validate_data
from quant.data.source_registry import source_status
from quant.pipeline import update_all as pipeline
from quant.pipeline.audit_prices import audit_prices
from quant.pipeline.update_calendar import refresh_calendar
from quant.storage.parquet_store import write_prices
from quant.data.nse_bhavcopy import UDIFF, parse_bhavcopy
from test_bhavcopy import archive
from test_calendar import fake_client


def test_completed_day_uses_indian_eod_cutoff():
    cfg = Config()
    tz = ZoneInfo('Asia/Kolkata')
    assert completed_day(cfg, datetime(2024, 7, 8, 18, 29, tzinfo=tz)) == date(2024, 7, 7)
    assert completed_day(cfg, datetime(2024, 7, 8, 18, 30, tzinfo=tz)) == date(2024, 7, 8)


def test_price_audit_counts_holes_and_corrupt_partitions(tmp_path):
    cfg = Config(data_dir=tmp_path)
    start, end = date(2024, 7, 8), date(2024, 7, 9)
    path = write_prices(parse_bhavcopy(archive(start, UDIFF), start), cfg.prices_dir)[0]
    refresh_calendar(cfg, start, end, client=fake_client())
    report = audit_prices(cfg, start, end)
    assert report['coverage_percent'] == 50 and report['missing_sessions'] == [str(end)]
    assert report['status'] == 'NOT_READY' and report['total_rows'] == 1
    path.write_bytes(b'broken')
    report = audit_prices(cfg, start, end)
    assert report['coverage_percent'] == 0 and len(report['corrupt_partitions']) == 1


def test_state_failure_does_not_advance_success_and_overlap_catches_missed_days(tmp_path):
    cfg = Config(data_dir=tmp_path)
    state = PipelineState(cfg)
    state.record('prices', status='READY', day='2024-07-08')
    state.record('prices', status='FAILED', day='2024-07-12', error='blocked')
    assert PipelineState(cfg).data['prices']['last_success'] == '2024-07-08'
    state.record('filings', status='READY', checked_from='2024-01-01', checked_through='2024-07-08')
    assert state.overlap_start('filings', date(2024, 1, 1), date(2024, 8, 1)) == date(2024, 6, 24)
    assert state.overlap_start('filings', date(2020, 1, 1), date(2024, 8, 1)) == date(2020, 1, 1)


def test_empty_foundation_cannot_be_ready(tmp_path):
    cfg = Config(data_dir=tmp_path)
    result = validate_data(cfg, date(2024, 7, 8), date(2024, 7, 9))
    assert result['status'] == 'NOT_READY' and not result['recommendation_allowed']
    assert list((tmp_path / 'reports').glob('data-health-*.json'))


def test_update_all_writes_health_after_calendar_failure(tmp_path, monkeypatch):
    cfg = Config(data_dir=tmp_path)
    monkeypatch.setattr(pipeline, 'refresh_calendar', lambda *args: (_ for _ in ()).throw(ValueError('blocked')))
    result = pipeline.update_all(cfg, date(2024, 7, 8), date(2024, 7, 9))
    assert result['status'] == 'NOT_READY' and 'calendar' in result['errors']


def test_switch_alone_does_not_make_source_ready(tmp_path):
    cfg = Config(data_dir=tmp_path, enable_fundamentals=True, enable_angel=True)
    statuses = source_status(cfg, {}, as_of=date(2024, 7, 9))
    assert statuses['nse_financials']['status'] == 'FAILED'
    assert statuses['angel']['status'] == 'NOT_IMPLEMENTED'
    assert statuses['nse_shareholding']['status'] == 'DISABLED'


def test_research_sql_views_query_parquet(tmp_path):
    from quant.storage.duckdb_store import query_dataset, research_connection
    cfg = Config(data_dir=tmp_path)
    day = date(2024, 7, 8)
    write_prices(parse_bhavcopy(archive(day, UDIFF), day), cfg.prices_dir)
    assert len(query_dataset(tmp_path, 'prices', start=day)) == 1
    assert query_dataset(tmp_path, 'prices', symbol="x' OR 1=1 --").empty
    with research_connection(tmp_path) as conn:
        assert conn.execute('select count(*) from prices').fetchone()[0] == 1
    with pytest.raises(ValueError):
        query_dataset(tmp_path, 'prices; drop table prices')
