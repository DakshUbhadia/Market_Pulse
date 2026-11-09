"""Restartable backfill; missing dates are explicitly unresolved, never invented."""
import argparse
import json
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo
from zipfile import BadZipFile

import requests

from quant.config import Config
from quant.data.http import Downloader, atomic_write
from quant.data.dhan_instruments import download_instruments
from quant.data.nse_bhavcopy import parse_bhavcopy, source_url
from quant.storage.parquet_store import write_parquet, write_prices
from quant.data.nse_client import NseSourceError


def run(config: Config, start: date, end: date, *, instruments=True, expected_dates=None,
        reuse_validated=False):
    if start > end:
        raise ValueError('Backfill start must not be after end')
    downloader = Downloader(config)
    requested_dates = (sorted(day for day in set(expected_dates) if start <= day <= end)
                       if expected_dates is not None else None)
    report = {'from': str(start), 'to': str(end), 'loaded': [], 'unresolved': [], 'failed': [],
              'calendar_supplied': expected_dates is not None,
              'expected_sessions': len(requested_dates) if requested_dates is not None else None}
    try:
        existing = {}
        if reuse_validated:
            from quant.data.nse_calendar import loaded_bhavcopy_evidence
            existing, _ = loaded_bhavcopy_evidence(config, start, end)
        if instruments:
            master = download_instruments(downloader)
            write_parquet(master, config.data_dir / 'normalized' / 'instruments'
                          / f'{master.snapshot_date.iloc[0]}.parquet')
        # Probe ALL calendar days by default: special weekend sessions must not be lost.
        days = requested_dates if requested_dates is not None else (
            start + timedelta(days=offset) for offset in range((end - start).days + 1))
        for day in days:
            if not start <= day <= end:
                continue
            if day in existing:
                report['loaded'].append({'date': str(day), 'rows': existing[day]['rows'], 'reused': True})
                continue
            url = source_url(day, config.nse_archives_url)
            destination = config.data_dir / 'raw' / 'nse' / str(day.year) / url.rsplit('/', 1)[-1]
            try:
                frame = parse_bhavcopy(downloader.fetch(url, destination), day, url)
                write_prices(frame, config.prices_dir)
                report['loaded'].append({'date': str(day), 'rows': len(frame)})
                print(f'{day}: loaded {len(frame)} rows', flush=True)
            except requests.HTTPError as error:
                status = error.response.status_code
                key = 'unresolved' if status == 404 else 'failed'
                report[key].append({'date': str(day), 'error': f'HTTP {status}'})
                print(f'{day}: {key} HTTP {status}', flush=True)
                if status in (401, 403, 429) or status >= 500:
                    break  # Stop a blocked source instead of repeating it for years of sessions.
            except (ValueError, OSError, BadZipFile, requests.RequestException) as error:
                report['failed'].append({'date': str(day), 'error': str(error)})
                print(f'{day}: failed {error}', flush=True)
    except Exception as error:
        report['failed'].append({'stage': 'bootstrap', 'error': str(error)})
        raise
    finally:
        downloader.close()
        attempted = {row['date'] for key in ('loaded', 'failed', 'unresolved')
                     for row in report[key] if 'date' in row}
        report['unattempted_sessions'] = ([str(day) for day in requested_dates if str(day) not in attempted]
                                          if requested_dates is not None else [])
        report['coverage'] = len(report['loaded']) / len(requested_dates) if requested_dates else None
        report['status'] = ('FAILED' if report['failed'] else
                            'INCOMPLETE' if report['unresolved'] or report['unattempted_sessions']
                            or (not report['loaded'] and requested_dates != []) else 'SUCCESS')
        path = config.data_dir / 'reports' / f'bootstrap-{start}-{end}.json'
        atomic_write(path, json.dumps(report, indent=2).encode())
    return report


def main():
    config = Config()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--from', dest='start', type=date.fromisoformat, default=date(2018, 1, 1))
    parser.add_argument('--to', dest='end', type=date.fromisoformat,
                        default=datetime.now(ZoneInfo(config.timezone)).date() - timedelta(days=1))
    parser.add_argument('--data-dir', type=Path)
    parser.add_argument('--skip-instruments', action='store_true')
    parser.add_argument('--trading-dates', type=Path,
                        help='Verified session calendar: one ISO date per line, including special sessions')
    parser.add_argument('--calendar', choices=('auto', 'cached', 'probe'), default='auto',
                        help='Refresh automatic calendar (default), use a generated calendar, or probe every date')
    args = parser.parse_args()
    if args.start > args.end:
        parser.error('--from must not be after --to')
    expected = None
    if args.trading_dates:
        expected = {date.fromisoformat(line.strip()) for line in args.trading_dates.read_text().splitlines()
                    if line.strip()}
        if not any(args.start <= day <= args.end for day in expected):
            parser.error('Trading calendar contains no dates in requested range')
    if args.data_dir:
        from dataclasses import replace
        config = replace(config, data_dir=args.data_dir)
    generated = expected is None and args.calendar != 'probe'
    try:
        if generated:
            from quant.pipeline.update_calendar import refresh_calendar, read_calendar
            if args.calendar == 'auto':
                refresh_calendar(config, args.start, args.end)
            calendar = read_calendar(config, args.start, args.end)
            expected = set(calendar.loc[calendar.is_trading_session, 'trade_date'].dt.date)
        elif args.trading_dates:
            # Generated text exports must not silently lose coverage/provenance information.
            metadata_path = args.trading_dates.with_suffix('.txt.json')
            if metadata_path.exists():
                from quant.data.http import sha256
                metadata = json.loads(metadata_path.read_text())
                if (metadata['sha256'] != sha256(args.trading_dates.read_bytes())
                        or metadata['from'] > str(args.start) or metadata['to'] < str(args.end)
                        or metadata['status'] != 'READY'):
                    raise ValueError('Generated session export is incomplete, changed, or needs review')
        report = run(config, args.start, args.end, instruments=not args.skip_instruments,
                     expected_dates=expected, reuse_validated=True)
        if generated:
            from quant.pipeline.update_calendar import reconcile_calendar
            health = reconcile_calendar(config, args.start, args.end)
            report['calendar_status'] = health['status']
            if health['status'] != 'READY':
                report['status'] = 'INCOMPLETE'
            atomic_write(config.data_dir / 'reports' / f'bootstrap-{args.start}-{args.end}.json',
                         json.dumps(report, indent=2).encode())
    except (NseSourceError, ValueError, OSError, requests.RequestException) as error:
        print(f'Backfill failed: {error}')
        return 1
    print(json.dumps({key: len(value) if key == 'loaded' else value for key, value in report.items()}, indent=2))
    return 0 if report['status'] == 'SUCCESS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
