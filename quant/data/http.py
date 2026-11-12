"""Polite downloads with verified cache and retained source provenance."""
import hashlib
import json
import os
import tempfile
import time
from zipfile import BadZipFile
from datetime import datetime, timezone
from pathlib import Path

import requests

from quant.config import Config


def sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def atomic_write(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as stream:
        temporary = Path(stream.name)
        stream.write(content)
    try:
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


class Downloader:
    def __init__(self, config: Config, session=None):
        self.config = config
        self.session = session or requests.Session()
        self.session.headers.update({'User-Agent': config.nse_user_agent,
                                     'Accept': '*/*'})
        self.last_request = 0.0

    def close(self):
        self.session.close()

    def fetch_parsed(self, url: str, destination: Path, parser):
        """A structurally invalid cache gets exactly one fresh network attempt."""
        for attempt in range(2):
            try:
                return parser(self.fetch(url, destination))
            except (ValueError, UnicodeError, BadZipFile):
                destination.unlink(missing_ok=True)
                destination.with_suffix(destination.suffix + '.json').unlink(missing_ok=True)
                if attempt:
                    raise

    def fetch(self, url: str, destination: Path) -> bytes:
        metadata = destination.with_suffix(destination.suffix + '.json')
        if destination.exists() and metadata.exists():
            try:
                info = json.loads(metadata.read_text(encoding='utf-8'))
                content = destination.read_bytes()
                if info['source_url'] == url and info['sha256'] == sha256(content):
                    return content
            except (ValueError, KeyError):
                pass
        for attempt in range(self.config.retries + 1):
            time.sleep(max(0, self.config.request_interval - (time.monotonic() - self.last_request)))
            self.last_request = time.monotonic()
            try:
                response = self.session.get(url, timeout=self.config.timeout)
                response.raise_for_status()
            except (requests.Timeout, requests.ConnectionError, requests.HTTPError) as error:
                status = getattr(getattr(error, 'response', None), 'status_code', None)
                if attempt == self.config.retries or (status is not None and status != 429 and status < 500):
                    raise
                time.sleep(min(30, 2 ** (attempt + 1)))
                continue
            content = response.content
            if not content or content.lstrip().lower().startswith((b'<!doctype html', b'<html')):
                raise ValueError(f'Empty or HTML response from {url}')
            atomic_write(destination, content)
            atomic_write(metadata, json.dumps({
                'source_url': url, 'sha256': sha256(content), 'bytes': len(content),
                'downloaded_at': datetime.now(timezone.utc).isoformat(),
                'fetched_at': datetime.now(timezone.utc).isoformat(),
                'http_status': response.status_code, 'parser_version': None,
            }, indent=2).encode())
            return content
        raise RuntimeError('Download attempts exhausted')
