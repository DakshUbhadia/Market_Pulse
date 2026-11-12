import pytest

from quant.config import Config
from quant.data.dhan_instruments import download_instruments
from quant.data.http import Downloader

pytestmark = pytest.mark.integration


def test_live_dhan(tmp_path):
    downloader = Downloader(Config(data_dir=tmp_path, retries=0, timeout=20))
    try:
        frame = download_instruments(downloader)
        assert len(frame) > 1000
        assert 'RELIANCE' in set(frame.nse_symbol)
        assert frame.instrument_id.is_unique
    finally:
        downloader.close()
