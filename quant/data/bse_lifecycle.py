"""Official BSE fallback evidence; reviewed economics use the shared schema."""
from urllib.parse import urlsplit

from quant.data.nse_lifecycle import archive_source


def archive_bse_evidence(config, url):
    if urlsplit(url).hostname != 'www.bseindia.com':
        raise ValueError('BSE evidence requires the official BSE host')
    return archive_source(config,url)
