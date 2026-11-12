from unittest.mock import Mock

import pytest

from quant.config import Config
from quant.data.http import Downloader


def test_invalid_cache_is_evicted_and_network_retried_once(tmp_path):
    session = Mock()
    session.get.side_effect = [Mock(content=b'bad', status_code=200),
                               Mock(content=b'good', status_code=200)]
    downloader = Downloader(Config(request_interval=0), session)
    path = tmp_path / 'cached.csv'
    downloader.fetch('https://example.test/a', path)

    def parse(content):
        if content != b'good':
            raise ValueError('Invalid structure')
        return content

    assert downloader.fetch_parsed('https://example.test/a', path, parse) == b'good'
    assert session.get.call_count == 2


def test_repeated_bad_object_is_not_left_cached(tmp_path):
    session = Mock()
    session.get.return_value = Mock(content=b'bad', status_code=200)
    downloader = Downloader(Config(request_interval=0), session)
    path = tmp_path / 'cached.csv'
    with pytest.raises(ValueError):
        downloader.fetch_parsed('https://example.test/a', path,
                                lambda _: (_ for _ in ()).throw(ValueError('bad')))
    assert session.get.call_count == 2
    assert not path.exists() and not path.with_suffix('.csv.json').exists()
