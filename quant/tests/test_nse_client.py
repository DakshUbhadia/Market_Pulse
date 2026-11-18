import json
from unittest.mock import Mock

import pytest
import requests

from quant.config import Config
from quant.data.http import sha256
from quant.data.nse_client import NseClient, NseSourceError


@pytest.fixture(autouse=True)
def no_transport_waits(monkeypatch):
    monkeypatch.setattr('quant.data.nse_client.time.sleep', lambda _: None)
    monkeypatch.setattr('quant.data.nse_client.random.uniform', lambda *_: 0)


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


def test_official_origin_migration_is_followed_once_and_archived(tmp_path):
    transport = session(response(status=301,headers={'Location':'https://www.nseindia.in/'}),
        response(),response(b'{"ok":true}'))
    with NseClient(config(tmp_path),session_factory=lambda:transport) as client:
        assert client.get_json('/api/example') == {'ok':True}
    assert transport.get.call_args_list[1].args[0] == 'https://www.nseindia.in/'
    assert len(list((tmp_path/'raw/nse/session').rglob('*.html'))) == 2


@pytest.mark.parametrize('warmup', [False, True])
def test_auth_retry_honors_source_cooldown(tmp_path, monkeypatch, warmup):
    sleeps = []
    monkeypatch.setattr('quant.data.nse_client.time.sleep', sleeps.append)
    blocked = response(status=403, headers={'Retry-After': '9'})
    first = session(*([blocked] if warmup else [response(), blocked]))
    second = session(response(), response(b'[]'))
    factory = Mock(side_effect=[first, second])
    with NseClient(config(tmp_path), session_factory=factory) as client:
        assert client.get_json('/api/example') == []
    assert 9 in sleeps
    assert factory.call_count == 2


def test_auth_long_cooldown_stops_before_session_renewal(tmp_path):
    first = session(response(status=403, headers={'Retry-After': '120'}))
    factory = Mock(return_value=first)
    with NseClient(config(tmp_path), session_factory=factory) as client:
        with pytest.raises(NseSourceError, match='cooldown') as caught:
            client.get_json('/api/example')
    assert caught.value.status == 'LIVE_SOURCE_UNAVAILABLE'
    assert caught.value.http_status == 403
    assert factory.call_count == 1


def test_pacing_jitter_preserves_request_floor(tmp_path, monkeypatch):
    sleeps = []
    monkeypatch.setattr('quant.data.nse_client.time.sleep', sleeps.append)
    monkeypatch.setattr('quant.data.nse_client.time.monotonic', lambda: 10)
    monkeypatch.setattr('quant.data.nse_client.random.uniform', lambda *_: 0.2)
    transport = session(response(), response(b'[]'))
    settings = Config(data_dir=tmp_path, request_interval=1.5, retries=0)
    with NseClient(settings, session_factory=lambda: transport) as client:
        client.get_json('/api/example')
    assert sleeps == [0.2, 1.7]


def test_probe_keeps_failure_after_success_without_using_cache(tmp_path, monkeypatch):
    from quant.pipeline import probe_nse_source as probe
    settings = config(tmp_path)
    transports = [session(response(), response()),
                  session(response(status=403)), session(response(status=403))]
    factory = Mock(side_effect=transports)
    monkeypatch.setattr(probe, 'NseClient', lambda cfg: NseClient(cfg, session_factory=factory))
    monkeypatch.setattr(probe, 'parse_holidays', lambda *_: list(range(5)))
    passed = probe.probe_nse_source(settings)
    failed = probe.probe_nse_source(settings)
    assert passed['status'] == 'LIVE_SMOKE_PASSED'
    assert failed['status'] == 'LIVE_SOURCE_UNAVAILABLE'
    assert failed['http_status'] == 403
    assert failed['observations'][0]['http_status'] == 403
    reports = list((tmp_path/'reports/source-probes').glob('*.json'))
    assert len(reports) == 2
    assert {json.loads(p.read_text())['status'] for p in reports} == {
        'LIVE_SMOKE_PASSED', 'LIVE_SOURCE_UNAVAILABLE'}
    assert factory.call_count == 3
    assert 'quant/data/nse_client.py' in failed['source_code_sha256']


def test_probe_rejects_successful_http_with_invalid_calendar(tmp_path, monkeypatch):
    from quant.pipeline import probe_nse_source as probe
    transport = session(response(), response())
    monkeypatch.setattr(probe, 'NseClient',
                        lambda cfg: NseClient(cfg, session_factory=lambda: transport))
    report = probe.probe_nse_source(config(tmp_path))
    assert report['status'] == 'LIVE_SOURCE_UNAVAILABLE'
    assert report['certifies_research_readiness'] is False
    assert report['observations'][0]['http_status'] == 200


def test_public_archive_does_not_depend_on_web_session_warmup(tmp_path):
    transport=session(response(b'<xbrl/>'))
    with NseClient(config(tmp_path),session_factory=lambda:transport) as client:
        assert client.get_bytes('https://nsearchives.nseindia.com/corporate/test.xml')==b'<xbrl/>'
        assert not client._warmed
    assert transport.get.call_count==1
    assert transport.get.call_args.args[0]=='https://nsearchives.nseindia.com/corporate/test.xml'


def test_blocked_static_archive_does_not_trigger_homepage_requests(tmp_path):
    transport=session(response(status=403))
    factory=Mock(return_value=transport)
    with NseClient(config(tmp_path),session_factory=factory) as client:
        with pytest.raises(NseSourceError,match='403'):
            client.get_bytes('https://nsearchives.nseindia.com/corporate/test.xml')
    assert transport.get.call_count==factory.call_count==1
