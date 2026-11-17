"""Official lifecycle inventories and circulars, archived before interpretation."""
from datetime import datetime, timezone
from html.parser import HTMLParser
from urllib.parse import urljoin, urlsplit
from uuid import uuid4

import requests

from quant.data.http import atomic_write, sha256
from quant.storage.research_store import write_json

SOURCE_PAGES = (
    'https://www.nseindia.in/static/list/list-of-companies-proposed-to-be-delisted',
    'https://www.nseindia.in/static/regulations/listing-compliance',
)
OFFICIAL_HOSTS = {'www.nseindia.com','www.nseindia.in','nsearchives.nseindia.com',
                  'archives.nseindia.com','www.bseindia.com'}


def archive_source(config, url, session=None):
    parsed = urlsplit(url)
    if parsed.scheme != 'https' or parsed.hostname not in OFFICIAL_HOSTS or parsed.username or parsed.password:
        raise ValueError('Lifecycle evidence must use an official exchange HTTPS host')
    transport = session or requests.Session()
    try:
        response = transport.get(url, timeout=config.timeout, allow_redirects=False,
            headers={'User-Agent':config.nse_user_agent})
    finally:
        if session is None:
            transport.close()
    now = datetime.now(timezone.utc)
    suffix = parsed.path.rsplit('.',1)[-1] if '.' in parsed.path.rsplit('/',1)[-1] else 'html'
    if suffix not in ('csv','xlsx','xls','pdf','json','html'):
        suffix = 'bin'
    path = config.data_dir/'raw/lifecycle'/f'{now:%Y%m%dT%H%M%S%f}-{uuid4().hex[:8]}.{suffix}'
    atomic_write(path,response.content)
    metadata = dict(source_url=url,source_sha256=sha256(response.content),sha256=sha256(response.content),
                    source_exchange='BSE' if parsed.hostname == 'www.bseindia.com' else 'NSE',
                    raw_path=str(path.relative_to(config.data_dir)),fetched_at=now.isoformat(),
                    first_seen_at=now.isoformat(),http_status=response.status_code)
    write_json(path.with_suffix(path.suffix+'.metadata.json'),metadata)
    response.raise_for_status()
    if response.status_code != 200 or not response.content:
        raise ValueError(f'Lifecycle source unavailable: HTTP {response.status_code}')
    return response.content, metadata


class InventoryLinks(HTMLParser):
    def __init__(self, base):
        super().__init__()
        self.base, self.links = base, []

    def handle_starttag(self, tag, attrs):
        url = urljoin(self.base,dict(attrs).get('href',''))
        if tag == 'a' and urlsplit(url).path.lower().endswith(('.csv','.xlsx','.xls')):
            if urlsplit(url).hostname in OFFICIAL_HOSTS:
                self.links.append(url)


def inventory_links(content, base):
    parser = InventoryLinks(base)
    parser.feed(content.decode('utf-8'))
    return sorted(set(url for url in parser.links if any(
        word in url.lower() for word in ('delist','suspend','suspension'))))
