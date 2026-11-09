import json
from unittest.mock import Mock

import pytest
import requests

from quant.config import Config
from quant.data.http import sha256
from quant.data.nse_client import NseClient, NseSourceError


def response(body=b'{}', status=200, headers=None):
    result = requests.Response()
    result.status_code = status
    result._content = body
    result.url = 'https://www.nseindia.com/api/example'
    result.headers.update(headers or {})
    return result


def session(*responses):
    result = Mock()
    result.headers = {}
    result.get.side_effect = responses
    return result


def config(tmp_path):
    return Config(data_dir=tmp_path, request_interval=0, retries=1)


def test_archive_before_json_parsing_and_no_secret_headers(tmp_path):
    transport = session(response(b'<html>home</html>'), response(b'{broken'))
    with NseClient(config(tmp_path), session_factory=lambda: transport) as client:
        with pytest.raises(NseSourceError, match='invalid JSON'):
            client.get_json('/api/example', dataset='calendar')
        raw = client.last_response
        assert raw.path.read_bytes() == b'{broken'
        metadata = json.loads(raw.path.with_suffix('.json.json').read_text())
        assert metadata['sha256'] == sha256(b'{broken')
        assert metadata['parser_version'] is None
        assert 'headers' not in metadata
        assert 'cookies' not in metadata


def test_reuses_warm_session_and_preserves_observations(tmp_path):
    transport = session(response(), response(b'[]'), response(b'[]'))
    with NseClient(config(tmp_path), session_factory=lambda: transport) as client:
        assert client.get_json('/api/example') == []
        first = client.last_response
        assert client.get_json('/api/example') == []
        second = client.last_response
    assert first.path != second.path
    assert first.path.exists() and second.path.exists()
    assert transport.get.call_count == 3  # One warmup, two endpoint calls.
    transport.close.assert_called_once()


def test_auth_refresh_once(tmp_path):
    first = session(response(), response(status=403))
    second = session(response(), response(b'{"ok":true}'))
    factory = Mock(side_effect=[first, second])
    with NseClient(config(tmp_path), session_factory=factory) as client:
        assert client.get_json('/api/example') == {'ok': True}
    assert factory.call_count == 2
    first.close.assert_called_once()


@pytest.mark.parametrize('warmup', [False, True])
def test_persistent_block_stops_after_one_refresh(tmp_path, warmup):
    responses = [response(status=403)] if warmup else [response(), response(status=403)]
    first, second = session(*responses), session(*responses)
    factory = Mock(side_effect=[first, second])
    with NseClient(config(tmp_path), session_factory=factory) as client:
        with pytest.raises(NseSourceError, match='403'):
            client.get_json('/api/example')
    assert factory.call_count == 2
    assert first.get.call_count == second.get.call_count == len(responses)


def test_retry_after_and_timeout(tmp_path, monkeypatch):
    sleeps = []
    monkeypatch.setattr('quant.data.nse_client.time.sleep', sleeps.append)
    transport = session(response(), response(status=429, headers={'Retry-After': '7'}), response(b'[]'))
    with NseClient(config(tmp_path), session_factory=lambda: transport) as client:
        assert client.get_json('/api/example') == []
    assert 7 in sleeps
    assert transport.get.call_args.kwargs['timeout'] == config(tmp_path).timeout


def test_long_retry_after_is_not_ignored(tmp_path):
    transport = session(response(), response(status=429, headers={'Retry-After': '120'}))
    with NseClient(config(tmp_path), session_factory=lambda: transport) as client:
        with pytest.raises(NseSourceError, match='cooldown'):
            client.get_json('/api/example')
    assert transport.get.call_count == 2


def test_transport_failure_is_bounded(tmp_path, monkeypatch):
    monkeypatch.setattr('quant.data.nse_client.time.sleep', lambda _: None)
    transport = session(response(), requests.Timeout(), requests.Timeout())
    with NseClient(config(tmp_path), session_factory=lambda: transport) as client:
        with pytest.raises(NseSourceError, match='timed out'):
            client.get_json('/api/example')
    assert transport.get.call_count == 3


def test_reject_foreign_host_and_redirect(tmp_path):
    transport = session(response(), response(status=302, headers={'Location': 'https://other.test'}))
    with NseClient(config(tmp_path), session_factory=lambda: transport) as client:
        with pytest.raises(ValueError, match='HTTPS hosts'):
            client.get_bytes('https://other.test/file')
        assert transport.get.call_count == 0
        with pytest.raises(NseSourceError, match='302'):
            client.get_json('/api/example')
    assert transport.get.call_args.kwargs['allow_redirects'] is False
