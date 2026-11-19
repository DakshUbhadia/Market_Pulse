"""Report research readiness separately from fresh live probes; never probes implicitly."""
import json
from datetime import datetime, timezone
from pathlib import Path

from quant.data.source_health import SourceHealth, source_health_gates
from quant.pipeline.check_research_ready import check_research_ready
from quant.storage.research_store import write_json


def validate_source_health(config, *, as_of, backtest_start=None, output=None, dataset_observations=None):
    # Revalidate archived inputs, rather than trusting an old READY JSON file.
    readiness = check_research_ready(config, as_of=as_of,
        requested_backtest_start=backtest_start, write=False)
    observations = []
    for path in sorted((config.data_dir/'reports/source-probes').glob('*.json')):
        observations.append(json.loads(path.read_text(encoding='utf-8')))
    probe = max(observations, key=lambda r: r.get('finished_at', ''), default={})
    from quant.data.source_health import classify_failure
    live = ('READY' if probe.get('status') == 'LIVE_SMOKE_PASSED' else
            'UNAVAILABLE' if probe else 'UNASSESSED')
    import pandas as pd
    stamp = pd.Timestamp(probe.get('finished_at')) if probe.get('finished_at') else None
    stale = bool(stamp is not None and (stamp.tzinfo is None or
        (pd.Timestamp.now(tz='UTC')-stamp).total_seconds() > 86400))
    if stale:
        live = 'DEGRADED'
    archived = readiness['status'] == 'READY'
    latest = readiness.get('latest_session')
    report = source_health_gates([SourceHealth(source_id='certified_research_inputs',
        historical_archive_ready='READY' if archived else 'UNAVAILABLE',
        current_eod_ready='READY' if archived and latest == str(as_of) else 'UNAVAILABLE',
        last_verified_session=latest, required_for_historical_research=True,
        required_for_forward_refresh=True), SourceHealth(source_id='nse_live_calendar',
        live_api_ready=live, last_live_probe=probe.get('finished_at'),
        last_success=probe.get('finished_at') if live == 'READY' else None,
        failure_class='STALE_SOURCE' if stale else classify_failure(http_status=probe.get('http_status')) if live == 'UNAVAILABLE' else None)],
        required_session=as_of, dataset_observations=dataset_observations)
    report['archive_audit'] = readiness
    report['live_probe_scope'] = 'CALENDAR_ONLY; unprobed API endpoints remain unassessed'
    report['generated_at'] = datetime.now(timezone.utc).isoformat()
    write_json(output or config.data_dir/'reports/source-health.json', report)
    return report


def main():
    from quant.pipeline.cli import parser_config
    from datetime import date
    parser, config = parser_config(__doc__)
    parser.add_argument('--backtest-start', type=date.fromisoformat)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--dataset-observations', type=Path)
    args = parser.parse_args()
    report = validate_source_health(args.config(config), as_of=args.end, backtest_start=args.backtest_start, output=args.output,
        dataset_observations=json.loads(args.dataset_observations.read_text(encoding='utf-8')) if args.dataset_observations else None)
    print(json.dumps(report, indent=2))
    return 0 if report['historical_research_ready'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
