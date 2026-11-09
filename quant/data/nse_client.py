"""NSE web transport with bounded recovery and immutable raw response archives."""
import json
import time
from dataclasses import dataclass
from datetime import datetime
from email.utils import parsedate_to_datetime
from pathlib import Path
from urllib.parse import urljoin, urlsplit
from uuid import uuid4
from zoneinfo import ZoneInfo

import requests

from quant.config import Config
from quant.data.http import atomic_write, sha256


class NseSourceError(RuntimeError):
    """An exchange response is blocked, unavailable, or no longer understood."""


class _SessionBlocked(NseSourceError):
    pass


@dataclass(frozen=True)
class RawResponse:
    source_url: str
    fetched_at: str
    sha256: str
    path: Path
    http_status: int

    def provenance(self):
        return {'source': 'NSE', 'source_url': self.source_url, 'fetched_at': self.fetched_at,
                'raw_sha256': self.sha256, 'raw_path': str(self.path)}


class NseClient:
    def __init__(self, config: Config, *, session_factory=requests.Session):
        self.config = config
        self._session_factory = session_factory
        self.session = self._new_session()
        self._warmed = False
        self._last_request = 0.0
        self.last_response: RawResponse | None = None

    def _new_session(self):
        session = self._session_factory()
        session.headers.update({'User-Agent': self.config.nse_user_agent, 'Accept': '*/*'})
        return session

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()

    def close(self):
        self.session.close()

    def invalidate_session(self):
        self.session.close()
        self.session = self._new_session()
        self._warmed = False

    def _url(self, path):
        url = urljoin(self.config.nse_base_url.rstrip('/') + '/', path)
        parsed = urlsplit(url)
        allowed = {urlsplit(self.config.nse_base_url).netloc,
                   urlsplit(self.config.nse_archives_url).netloc}
        if parsed.scheme != 'https' or parsed.netloc not in allowed or parsed.username or parsed.password:
            raise ValueError('NseClient only accepts configured NSE HTTPS hosts')
        return url

    def _archive(self, response, dataset, suffix):
        if not dataset.replace('_', '').isalnum():
            raise ValueError('Invalid raw dataset name')
        now = datetime.now(ZoneInfo(self.config.timezone))
        digest = sha256(response.content)
        # A new observation never replaces an older response or its fetched_at timestamp.
        path = (self.config.data_dir / 'raw' / 'nse' / dataset / f'{now:%Y-%m-%d}'
                / f'{now:%H%M%S%f}-{digest[:16]}-{uuid4().hex[:8]}.{suffix}')
        atomic_write(path, response.content)
        record = RawResponse(response.url, now.isoformat(), digest, path, response.status_code)
        atomic_write(path.with_suffix(path.suffix + '.json'), json.dumps({
            'source': 'NSE', 'source_url': response.url, 'fetched_at': record.fetched_at,
            'sha256': digest, 'http_status': response.status_code, 'parser_version': None,
        }, indent=2).encode())
        self.last_response = record
        return record

    def _retry_delay(self, response, attempt):
        delay = min(30, 2 ** (attempt + 1))
        if response is not None:
            value = response.headers.get('Retry-After')
            if value:
                try:
                    delay = max(delay, float(value))
                except ValueError:
                    try:
                        until = parsedate_to_datetime(value)
                        delay = max(delay, (until - datetime.now(until.tzinfo)).total_seconds())
                    except (ValueError, TypeError):
                        pass
        # A long server-requested cooldown is a clear failure, not permission to retry early.
        if delay > 60:
            raise NseSourceError('NSE requested a longer cooldown; try again later')
        time.sleep(delay)

    def _request(self, url, *, params=None, referer=None, dataset='web', suffix='bin', warmup=False):
        for attempt in range(self.config.retries + 1):
            time.sleep(max(0, self.config.request_interval - (time.monotonic() - self._last_request)))
            self._last_request = time.monotonic()
            response = None
            try:
                headers = {'Accept': '*/*'} if warmup else {
                    'Referer': referer or self.config.nse_base_url + '/'}
                response = self.session.get(url, params=params, timeout=self.config.timeout,
                                            headers=headers,
                                            allow_redirects=False)
            except (requests.Timeout, requests.ConnectionError):
                if attempt == self.config.retries:
                    raise NseSourceError('NSE request timed out or connection failed') from None
            else:
                self._archive(response, dataset, suffix)
                if response.status_code != 429 and response.status_code < 500:
                    return response
                if attempt == self.config.retries:
                    raise NseSourceError(f'NSE source failed with HTTP {response.status_code}')
            self._retry_delay(response, attempt)
        raise NseSourceError('NSE attempts exhausted')

    def _warm(self):
        response = self._request(self.config.nse_base_url + '/', dataset='session', suffix='html', warmup=True)
        if response.status_code in (401, 403):
            raise _SessionBlocked(f'NSE session warm-up failed with HTTP {response.status_code}')
        if response.status_code != 200:
            raise NseSourceError(f'NSE session warm-up failed with HTTP {response.status_code}')
        self._warmed = True

    def get_bytes(self, url: str, *, referer=None, params=None, dataset='web', suffix='bin') -> bytes:
        url = self._url(url)
        for auth_attempt in range(2):
            try:
                if not self._warmed:
                    self._warm()
                response = self._request(url, params=params, referer=referer, dataset=dataset, suffix=suffix)
                if response.status_code in (401, 403):
                    raise _SessionBlocked(f'NSE source blocked with HTTP {response.status_code}')
                break
            except _SessionBlocked:
                if auth_attempt == 1:
                    raise
                self.invalidate_session()
        if response.status_code != 200:
            raise NseSourceError(f'NSE source failed with HTTP {response.status_code}')
        if not response.content:
            raise NseSourceError('NSE returned an empty response')
        return response.content

    def get_json(self, path: str, *, params=None, referer=None, dataset='web') -> dict | list:
        content = self.get_bytes(path, params=params, referer=referer, dataset=dataset, suffix='json')
        try:
            payload = json.loads(content)
        except (ValueError, UnicodeError):
            raise NseSourceError('NSE returned invalid JSON (possibly a challenge page); raw response archived') from None
        if not isinstance(payload, (dict, list)):
            raise NseSourceError('NSE JSON schema changed: expected an object or array')
        return payload
