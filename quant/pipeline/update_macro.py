"""Archive configured RBI series and report missing/stale mirror data honestly."""
import json
from datetime import datetime
from zoneinfo import ZoneInfo

import requests

from quant.data.http import Downloader, atomic_write, sha256
from quant.data.normalization import write_observation
from quant.data.rbi_macro import parse_macro, registry
from quant.pipeline.state import PipelineState


def update_macro(config, start, end):
    state = PipelineState(config)
    if not config.enable_rbi:
        state.record('rbi', status='DISABLED')
        return {'status': 'DISABLED'}
    now = datetime.now(ZoneInfo(config.timezone))
    downloader = Downloader(config)
    result = {}
    try:
        for name, spec in registry().items():
            url = config.rbi_api_base.rstrip('/') + '/api/tables/' + spec['table'] + '/csv'
            path = config.data_dir / 'raw' / 'rbi' / name / f'{now:%Y-%m-%d}.csv'
            try:
                frame = downloader.fetch_parsed(url, path, lambda content: parse_macro(
                    content, name, spec, url=url, fetched_at=now.isoformat()))
                frame = frame[frame.observation_date.dt.date.between(start, end)]
                if frame.empty:
                    raise ValueError('No macro data in requested period')
                digest = sha256(path.read_bytes())
                write_observation(frame, config.data_dir / 'normalized' / 'macro' / name, digest, now)
                latest = frame.observation_date.max().date()
                result[name] = {'status': 'STALE' if (end - latest).days > spec['max_age_days'] else 'READY',
                                'latest_date': str(latest), 'rows': len(frame), 'point_in_time_status': 'UNCERTAIN'}
            except (ValueError, OSError, requests.RequestException) as error:
                result[name] = {'status': 'FAILED', 'error': str(error)}
    finally:
        downloader.close()
    status = 'READY' if all(row['status'] == 'READY' for row in result.values()) else 'FAILED'
    report = {'status': status, 'series': result, 'point_in_time_status': 'UNCERTAIN'}
    state.record('rbi', **report)
    atomic_write(config.data_dir / 'reports' / f'macro-{end}.json', json.dumps(report, indent=2).encode())
    return report


def main():
    from quant.pipeline.cli import parser_config
    parser, config = parser_config(__doc__)
    args = parser.parse_args()
    report = update_macro(args.config(config), args.start, args.end)
    print(json.dumps(report, indent=2))
    return 0 if report['status'] in ('READY', 'DISABLED') else 1


if __name__ == '__main__':
    raise SystemExit(main())
