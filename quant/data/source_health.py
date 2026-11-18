"""Independent, fail-closed archive, EOD and live transport observations."""
from dataclasses import asdict, dataclass
from enum import StrEnum


class HealthStatus(StrEnum):
    READY = 'READY'
    DEGRADED = 'DEGRADED'
    UNAVAILABLE = 'UNAVAILABLE'
    UNASSESSED = 'UNASSESSED'


FAILURE_CLASSES = {
    'HTTP_403_ACCESS_DENIED', 'HTTP_429_RATE_LIMIT', 'HTTP_5XX_SOURCE_FAILURE',
    'NETWORK_FAILURE', 'SCHEMA_CHANGED', 'ARCHIVE_NOT_FOUND',
    'CHECKSUM_MISMATCH', 'STALE_SOURCE',
}


def classify_failure(error=None, *, http_status=None, checksum_mismatch=False,
                     stale=False, schema_changed=False, archive_missing=False):
    status = http_status or getattr(error, 'http_status', None)
    if status is None:
        status = getattr(getattr(error, 'response', None), 'status_code', None)
    if checksum_mismatch:
        return 'CHECKSUM_MISMATCH'
    if stale:
        return 'STALE_SOURCE'
    if status == 403:
        return 'HTTP_403_ACCESS_DENIED'
    if status == 429:
        return 'HTTP_429_RATE_LIMIT'
    if status is not None and 500 <= status < 600:
        return 'HTTP_5XX_SOURCE_FAILURE'
    if archive_missing or status == 404 or isinstance(error, FileNotFoundError):
        return 'ARCHIVE_NOT_FOUND'
    if schema_changed or isinstance(error, (ValueError, KeyError)):
        return 'SCHEMA_CHANGED'
    return 'NETWORK_FAILURE'


@dataclass(frozen=True)
class SourceHealth:
    source_id: str
    historical_archive_ready: str = 'UNASSESSED'
    current_eod_ready: str = 'UNASSESSED'
    live_api_ready: str = 'UNASSESSED'
    last_verified_session: str | None = None
    last_live_probe: str | None = None
    last_success: str | None = None
    failure_class: str | None = None
    required_for_historical_research: bool = False
    required_for_forward_refresh: bool = False

    def __post_init__(self):
        if not self.source_id.strip():
            raise ValueError('Source ID is required')
        for value in (self.historical_archive_ready, self.current_eod_ready, self.live_api_ready):
            HealthStatus(value)
        if self.failure_class is not None and self.failure_class not in FAILURE_CLASSES:
            raise ValueError('Unknown source failure classification')


def source_health_gates(sources, *, required_session, model_approved=False,
                        monitoring_ready=False, incidents_resolved=False):
    rows = [asdict(row) if isinstance(row, SourceHealth) else asdict(SourceHealth(**row)) for row in sources]
    if len({r['source_id'] for r in rows}) != len(rows):
        raise ValueError('Duplicate source health observations')
    historical = [r for r in rows if r['required_for_historical_research']]
    eod = [r for r in rows if r['required_for_forward_refresh']]
    history_ready = bool(historical) and all(r['historical_archive_ready'] == 'READY'
        and r['failure_class'] not in ('CHECKSUM_MISMATCH', 'ARCHIVE_NOT_FOUND') for r in historical)
    refresh_ready = bool(eod) and all(r['current_eod_ready'] == 'READY'
        and r['failure_class'] not in ('CHECKSUM_MISMATCH', 'ARCHIVE_NOT_FOUND', 'STALE_SOURCE')
        and r['last_verified_session'] == str(required_session) for r in eod)
    live = [r['live_api_ready'] for r in rows if r['live_api_ready'] != 'UNASSESSED']
    archive_available = any(r['historical_archive_ready'] == 'READY' for r in rows)
    live_status = ('UNASSESSED' if not live else
                   'READY' if all(s == 'READY' for s in live) else
                   'UNAVAILABLE' if all(s == 'UNAVAILABLE' for s in live) and not archive_available else 'DEGRADED')
    return dict(historical_research_ready=history_ready, forward_refresh_ready=refresh_ready,
        live_source_health=live_status,
        production_publish_ready=bool(history_ready and refresh_ready and model_approved
                                      and monitoring_ready and incidents_resolved),
        required_session=str(required_session), sources=rows)
