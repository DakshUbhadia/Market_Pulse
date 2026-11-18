"""Fresh NSE calendar smoke probe; never substitutes for the full live suite."""
from datetime import datetime, timezone
import json
from pathlib import Path
from uuid import uuid4
from zoneinfo import ZoneInfo

from quant.data.nse_calendar import parse_holidays
from quant.data.nse_client import NseClient, NseSourceError
from quant.storage.research_store import digest_file, git_commit, write_json


def probe_nse_source(config):
    started = datetime.now(timezone.utc)
    repo = Path(__file__).resolve().parents[2]
    sources = ('quant/data/nse_client.py', 'quant/data/nse_calendar.py',
               'quant/config.py', 'quant/pipeline/probe_nse_source.py')
    report = dict(schema_version=1, started_at=started.isoformat(), git_commit=git_commit(),
                  source_code_sha256={name: digest_file(repo/name) for name in sources},
                  transport_policy=dict(base_url=config.nse_base_url,
                                        timeout_seconds=config.timeout,
                                        request_interval_seconds=config.request_interval,
                                        retries=config.retries, max_session_renewals=1),
                  scope='LIVE_CALENDAR_SMOKE_ONLY', cached_success_allowed=False,
                  certifies_research_readiness=False, observations=[])
    with NseClient(config) as client:
        try:
            year = started.astimezone(ZoneInfo(config.timezone)).year
            payload = client.get_json('/api/holiday-master', params={'type': 'trading', 'year': year},
                                      dataset='source_probe')
            events = parse_holidays(payload, year, client.last_response)
            if len(events) < 5:
                raise NseSourceError('Calendar smoke returned fewer than five holidays')
            report.update(status='LIVE_SMOKE_PASSED', holiday_count=len(events))
        except (NseSourceError, ValueError) as error:
            report.update(status='LIVE_SOURCE_UNAVAILABLE', error=str(error),
                          http_status=getattr(error, 'http_status', None))
        if client.last_response is not None:
            raw = client.last_response
            report['observations'].append(dict(**raw.provenance(), http_status=raw.http_status))
    report['finished_at'] = datetime.now(timezone.utc).isoformat()
    # Each invocation keeps its own report and raw observations, including failures.
    path = config.data_dir/'reports/source-probes'/f'{started:%Y%m%dT%H%M%S%f}-{uuid4().hex}.json'
    report['report_path'] = str(path)
    write_json(path, report)
    return report


def main():
    from quant.pipeline.cli import parser_config
    parser, config = parser_config(__doc__)
    args = parser.parse_args()
    report = probe_nse_source(args.config(config))
    print(json.dumps(report, indent=2))
    return 0 if report['status'] == 'LIVE_SMOKE_PASSED' else 1


if __name__ == '__main__':
    raise SystemExit(main())
