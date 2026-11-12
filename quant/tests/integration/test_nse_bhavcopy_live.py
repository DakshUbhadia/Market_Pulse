from datetime import date, datetime, timedelta
from io import BytesIO
from zipfile import is_zipfile
from zoneinfo import ZoneInfo

import pytest

from quant.config import Config
from quant.data.http import Downloader
from quant.data.nse_bhavcopy import parse_bhavcopy, source_url, validate_bars

pytestmark = pytest.mark.integration


@pytest.mark.parametrize('day', [date(2024, 7, 5), date(2024, 7, 8), None])
def test_live_bhavcopy(tmp_path, day):
    config = Config(data_dir=tmp_path, retries=0, timeout=20)
    if day is None:
        from quant.pipeline.cli import completed_day
        from quant.pipeline.update_calendar import refresh_calendar
        target = completed_day(config)
        calendar, _ = refresh_calendar(config, target - timedelta(days=14), target)
        # The exchange calendar, rather than a weekday guess, selects the recent session.
        day = calendar.loc[calendar.is_trading_session, 'trade_date'].max().date()
    downloader = Downloader(config)
    try:
        url = source_url(day, config.nse_archives_url)
        content = downloader.fetch(url, tmp_path / f'{day}.zip')
        assert is_zipfile(BytesIO(content))
        frame = parse_bhavcopy(content, day, url)
        assert len(frame) > 1000
        assert 'RELIANCE' in set(frame.symbol)
        validate_bars(frame)
    finally:
        downloader.close()
