"""Official source admission and an archived client for reviewed fallback URLs."""
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit
from uuid import uuid4

import requests

from quant.data.http import atomic_write, sha256
from quant.data.nse_client import RawResponse
from quant.storage.research_store import write_json

NSE_HOSTS = {'www.nseindia.com', 'www.nseindia.in', 'nsearchives.nseindia.com',
             'nsearchives.nseindia.in', 'archives.nseindia.com'}
BSE_HOSTS = {'www.bseindia.com', 'api.bseindia.com', 'api.bseindia.in'}


def validate_official_source(row, *, issuer_hosts=()):
    url = urlsplit(row['source_url'])
    if url.scheme != 'https' or not url.hostname or url.username or url.password or url.port not in (None, 443):
        raise ValueError('Official filing evidence requires a credential-free HTTPS URL')
    kind = row.get('source_type')
    if kind == 'NSE_OFFICIAL' and url.hostname in NSE_HOSTS and row.get('source_exchange') == 'NSE':
        return row
    if not row.get('reason_primary_source_unavailable'):
        raise ValueError('Fallback requires a recorded reason NSE cannot supply the source byte')
    if kind == 'BSE_OFFICIAL' and url.hostname in BSE_HOSTS and row.get('source_exchange') == 'BSE':
        if row.get('cross_listing_verified') is not True or not row.get('bse_security_code'):
            raise ValueError('BSE fallback requires a verified cross-listed security mapping')
        return row
    if kind == 'ISSUER_IR' and url.hostname in set(issuer_hosts):
        if not row.get('issuer_host_reviewed_by') or not row.get('reason_exchange_archive_unavailable'):
            raise ValueError('Issuer fallback requires reviewed ownership and exchange archive exhaustion')
        return row
    raise ValueError('Source is not an admitted official exchange or reviewed issuer host')


class OfficialDocumentClient:
    """Fetch exact reviewed URLs, retaining even HTTP failure response bytes."""
    def __init__(self, config, provenance, *, issuer_hosts=(), session=None):
        self.config, self.provenance = config, provenance
        self.issuer_hosts = issuer_hosts
        self.session = session or requests.Session()
        self.last_response = None

    def close(self):
        self.session.close()

    def get_bytes(self, url, *, dataset='financial_xbrl', suffix='xml'):
        validate_official_source(dict(self.provenance, source_url=url), issuer_hosts=self.issuer_hosts)
        try:
            response = self.session.get(url, timeout=self.config.timeout, allow_redirects=False)
            now = datetime.now(timezone.utc).isoformat()
            path = self.config.data_dir/'raw/official_filing_discovery'/f'{uuid4().hex}.{suffix}'
            atomic_write(path, response.content)
            raw = RawResponse(url, now, sha256(response.content), path, response.status_code)
            self.last_response = raw
            write_json(path.with_suffix(path.suffix+'.json'), dict(self.provenance,
                source_url=url, retrieved_at=now, sha256=raw.sha256, http_status=response.status_code))
            response.raise_for_status()
            if response.status_code != 200:
                raise ValueError('Review the official redirect target before acquisition')
            return response.content
        except requests.RequestException as error:
            raise OSError(str(error)) from error
