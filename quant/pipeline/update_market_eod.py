"""Restartable EOD ingestion: recheck all expected partitions, including old holes."""
import json
from datetime import datetime
from zoneinfo import ZoneInfo

import requests

from quant.data import nse_delivery, nse_indices, nse_security_master, nse_vix
from quant.data.nse_flows import PATH as FLOWS_PATH, parse_flows
from quant.data.nse_client import NseClient, NseSourceError
from quant.data.http import Downloader, atomic_write
from quant.data.security_history import build_security_history
from quant.pipeline.bootstrap_history import run as bootstrap
from quant.pipeline.state import PipelineState
from quant.pipeline.update_calendar import read_calendar, reconcile_calendar
from quant.storage.duckdb_store import query_prices
from quant.storage.parquet_store import write_parquet


def daily_path(config, dataset, day):
    return config.data_dir / 'normalized' / dataset / f'year={day.year}' / f'month={day.month:02d}' / f'{day}.parquet'


def update_market_eod(config, start, end):
    calendar = read_calendar(config, start, end)
    sessions = sorted(calendar.loc[calendar.is_trading_session, 'trade_date'].dt.date)
    state = PipelineState(config)
    report = {}
    downloader = Downloader(config)
    today = datetime.now(ZoneInfo(config.timezone)).date()
    try:
        # This is today's snapshot even when a historical backfill is requested.
        url = nse_security_master.source_url(config.nse_archives_url)
        path = config.data_dir / 'raw' / 'nse' / 'security_master' / f'{today}.csv'
        try:
            master = downloader.fetch_parsed(url, path,
                lambda data: nse_security_master.parse_security_master(data, today, url))
            write_parquet(master, config.data_dir / 'normalized' / 'instruments' / 'nse' / f'{today}.parquet')
            report['nse_security_master'] = {'status': 'READY', 'rows': len(master)}
        except (ValueError, OSError, requests.RequestException) as error:
            report['nse_security_master'] = {'status': 'FAILED', 'error': str(error)}
        state.record('nse_security_master', day=today, **report['nse_security_master'])
        prices = bootstrap(config, start, end, instruments=False, expected_dates=sessions, reuse_validated=True)
        report['nse_bhavcopy'] = {'status': 'READY' if prices['status'] == 'SUCCESS' else 'FAILED',
                                  'loaded': len(prices['loaded']), 'failed': prices['failed'],
                                  'missing': prices['unresolved'] + prices['unattempted_sessions']}
        if prices['loaded']:
            last_price = max(row['date'] for row in prices['loaded'])
        else:
            last_price = None
        state.record('nse_bhavcopy', day=last_price, **report['nse_bhavcopy'])
        reconcile_calendar(config, start, end)
        for dataset, adapter in [('delivery', nse_delivery), ('indices', nse_indices)]:
            loaded, failures = [], []
            for day in sessions:
                target = daily_path(config, dataset, day)
                # Reparse verified raw inputs on each run (no network when cached),
                # so corrupt normalized partitions are automatically repaired.
                url = adapter.source_url(day, config.nse_archives_url)
                raw = config.data_dir / 'raw' / 'nse' / dataset / str(day.year) / url.rsplit('/', 1)[-1]
                try:
                    parser = adapter.parse_delivery if dataset == 'delivery' else adapter.parse_indices
                    frame = downloader.fetch_parsed(url, raw, lambda data: parser(data, day, url))
                    write_parquet(frame, target)
                    if dataset == 'indices':
                        vix = nse_vix.from_indices(frame)
                        write_parquet(vix, daily_path(config, 'vix', day))
                    loaded.append(str(day))
                except (ValueError, OSError, requests.RequestException) as error:
                    failures.append({'date': str(day), 'error': str(error)})
                    status = getattr(getattr(error, 'response', None), 'status_code', None)
                    if status in (401, 403, 429) or (status is not None and status >= 500):
                        break
                    if isinstance(error, (requests.ConnectionError, requests.Timeout)):
                        break
            report['nse_' + dataset] = {'status': 'READY' if len(loaded) == len(sessions) else 'FAILED',
                                         'loaded_sessions': len(loaded), 'expected_sessions': len(sessions),
                                         'coverage_percent': 100 * len(loaded) / len(sessions) if sessions else None,
                                         'failures': failures}
            state.record('nse_' + dataset, day=max(loaded) if loaded else None, **report['nse_' + dataset])
        report['nse_vix'] = dict(report['nse_indices'])
        state.record('nse_vix', **report['nse_vix'])
        try:
            history = build_security_history(query_prices(config.prices_dir,
                columns=['trade_date', 'symbol', 'series', 'isin']))
            write_parquet(history, config.data_dir / 'normalized' / 'security_history' / 'identities.parquet')
            unresolved = int((history.identity_status == 'UNRESOLVED').sum())
            report['security_history'] = {'status': 'READY', 'intervals': len(history), 'unresolved': unresolved}
        except (ValueError, OSError, KeyError) as error:
            report['security_history'] = {'status': 'FAILED', 'error': str(error)}
        state.record('security_history', **report['security_history'])
        if config.enable_fiidii:
            try:
                with NseClient(config) as client:
                    payload = client.get_json(FLOWS_PATH, dataset='flows')
                    frame = parse_flows(payload, client.last_response)
                    from quant.data.normalization import write_observation
                    write_observation(frame, config.data_dir / 'normalized' / 'fii_dii',
                                      client.last_response.sha256, client.last_response.fetched_at)
                    report['nse_flows'] = {'status': 'READY', 'latest_date': str(frame.trade_date.max().date()),
                                           'historical_backfill': False}
            except (ValueError, OSError, NseSourceError) as error:
                report['nse_flows'] = {'status': 'FAILED', 'error': str(error)}
        else:
            report['nse_flows'] = {'status': 'DISABLED'}
        state.record('nse_flows', **report['nse_flows'])
    finally:
        downloader.close()
        atomic_write(config.data_dir / 'reports' / f'market-eod-{end}.json', json.dumps(report, indent=2).encode())
    return report


def main():
    from quant.pipeline.cli import parser_config
    parser, config = parser_config(__doc__)
    parser.add_argument('--calendar', choices=('auto', 'cached'), default='auto')
    args = parser.parse_args()
    try:
        config = args.config(config)
        if args.calendar == 'auto':
            from quant.pipeline.update_calendar import refresh_calendar
            refresh_calendar(config, args.start, args.end)
        report = update_market_eod(config, args.start, args.end)
        print(json.dumps(report, indent=2))
        return 0 if all(report[name]['status'] == 'READY' for name in
                        ('nse_security_master', 'nse_bhavcopy', 'nse_indices', 'nse_vix', 'security_history')) else 1
    except (ValueError, OSError, requests.RequestException, NseSourceError) as error:
        print(f'EOD update failed: {error}')
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
