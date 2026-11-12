from datetime import date, datetime
from zoneinfo import ZoneInfo

import pandas as pd
import pytest

from quant.config import Config
from quant.data import nse_delivery, nse_indices, nse_security_master, nse_vix
from quant.data.http import Downloader
from quant.data.nse_client import NseClient
from quant.data.nse_corporate_actions import parse_corporate_actions
from quant.data.nse_bhavcopy import parse_bhavcopy, source_url
from quant.features.adjustments import adjust_prices
from quant.features.returns import calculate_returns

pytestmark = pytest.mark.integration


def test_live_market_reports(tmp_path):
    config = Config(data_dir=tmp_path, retries=0, timeout=20)
    downloader = Downloader(config)
    day = date(2024, 7, 8)
    try:
        url = nse_delivery.source_url(day, config.nse_archives_url)
        delivery = nse_delivery.parse_delivery(downloader.fetch(url, tmp_path / 'delivery.csv'), day, url)
        assert len(delivery) > 1000 and 'RELIANCE' in set(delivery.symbol)
        url = nse_indices.source_url(day, config.nse_archives_url)
        indices = nse_indices.parse_indices(downloader.fetch(url, tmp_path / 'indices.csv'), day, url)
        assert nse_indices.REQUIRED_INDICES.issubset(set(indices.index_name))
        assert nse_vix.from_indices(indices).close.iloc[0] > 0
        url = nse_security_master.source_url(config.nse_archives_url)
        master = nse_security_master.parse_security_master(downloader.fetch(url, tmp_path / 'master.csv'),
            datetime.now(ZoneInfo(config.timezone)).date(), url)
        assert len(master) > 1000 and 'RELIANCE' in set(master.symbol)
    finally:
        downloader.close()


def test_known_reliance_bonus_reconciles(tmp_path):
    config = Config(data_dir=tmp_path, retries=0, timeout=20)
    with NseClient(config) as client:
        payload = client.get_json('/api/corporates-corporateActions',
            params={'index': 'equities', 'symbol': 'RELIANCE', 'from_date': '25-10-2024',
                    'to_date': '29-10-2024'}, dataset='corporate_actions')
        actions = parse_corporate_actions(payload, client.last_response)
    bonus = actions[(actions.symbol == 'RELIANCE') & (actions.action_type == 'BONUS')]
    assert len(bonus) == 1 and bonus.parse_status.iloc[0] == 'PARSED'
    downloader = Downloader(config)
    try:
        bars = []
        for day in (date(2024, 10, 25), date(2024, 10, 28)):
            url = source_url(day, config.nse_archives_url)
            frame = parse_bhavcopy(downloader.fetch(url, tmp_path / f'{day}.zip'), day, url)
            bars.append(frame[(frame.symbol == 'RELIANCE') & (frame.series == 'EQ')])
        result = calculate_returns(adjust_prices(pd.concat(bars, ignore_index=True), bonus))
        assert result.raw_return.iloc[-1] < -.4
        assert abs(result.adjusted_return.iloc[-1]) < .1
    finally:
        downloader.close()
