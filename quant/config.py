"""Local configuration. Process environment takes precedence over the root .env."""
import os
import math
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo

from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(REPO_ROOT / '.env', override=False)


def env(name, default, convert=str):
    return field(default_factory=lambda: convert(os.getenv(name, default)))


def boolean(value):
    if value.strip().lower() not in ('true', 'false'):
        raise ValueError('Feature switches must be true or false')
    return value.strip().lower() == 'true'


@dataclass(frozen=True)
class Config:
    data_dir: Path = env('QUANT_DATA_DIR', './data', Path)
    timezone: str = env('QUANT_TIMEZONE', 'Asia/Kolkata')
    timeout: float = env('QUANT_HTTP_TIMEOUT_SECONDS', '45', float)
    request_interval: float = env('QUANT_NSE_REQUEST_INTERVAL_SECONDS', '1.5', float)
    retries: int = env('QUANT_HTTP_RETRIES', '3', int)
    nse_base_url: str = env('QUANT_NSE_BASE_URL', 'https://www.nseindia.com')
    nse_archives_url: str = env('QUANT_NSE_ARCHIVES_URL', 'https://nsearchives.nseindia.com')
    nse_user_agent: str = env('QUANT_NSE_USER_AGENT', 'Mozilla/5.0')
    rbi_api_base: str = env('QUANT_RBI_API_BASE', 'https://data-api.dbie.rbihub.in')
    mongo_publish: bool = env('QUANT_MONGO_PUBLISH', 'false', boolean)
    enable_angel: bool = env('QUANT_ENABLE_ANGEL', 'false', boolean)
    enable_fundamentals: bool = env('QUANT_ENABLE_FUNDAMENTALS', 'false', boolean)
    enable_shareholding: bool = env('QUANT_ENABLE_SHAREHOLDING', 'false', boolean)
    enable_announcements: bool = env('QUANT_ENABLE_ANNOUNCEMENTS', 'false', boolean)
    enable_fiidii: bool = env('QUANT_ENABLE_FIIDII', 'false', boolean)
    enable_rbi: bool = env('QUANT_ENABLE_RBI', 'false', boolean)
    enable_derivatives: bool = env('QUANT_ENABLE_DERIVATIVES', 'false', boolean)

    def __post_init__(self):
        path = Path(self.data_dir).expanduser()
        object.__setattr__(self, 'data_dir', path if path.is_absolute() else REPO_ROOT / path)
        ZoneInfo(self.timezone)
        if not math.isfinite(self.timeout) or self.timeout <= 0:
            raise ValueError('QUANT_HTTP_TIMEOUT_SECONDS must be positive and finite')
        if not math.isfinite(self.request_interval) or self.request_interval < 0:
            raise ValueError('QUANT_NSE_REQUEST_INTERVAL_SECONDS must be nonnegative and finite')
        if not isinstance(self.retries, int) or not 0 <= self.retries <= 5:
            raise ValueError('QUANT_HTTP_RETRIES must be between 0 and 5')
        for name in ('nse_base_url', 'nse_archives_url', 'rbi_api_base'):
            url = urlsplit(getattr(self, name))
            if url.scheme != 'https' or not url.hostname or url.username or url.password or url.query or url.fragment:
                raise ValueError(f'{name} must be an HTTPS base URL without credentials or query parameters')

    @property
    def prices_dir(self) -> Path:
        return self.data_dir / 'normalized' / 'prices'

    @property
    def calendar_path(self) -> Path:
        return self.data_dir / 'normalized' / 'calendar' / 'nse_sessions.parquet'

    @property
    def calendar_text_path(self) -> Path:
        return self.data_dir / 'reference' / 'nse_sessions.txt'
