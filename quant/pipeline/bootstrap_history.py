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


def run(config: Config, start: date, end: date, *, instruments=True, expected_dates=None):
    downloader = Downloader(config)
    report = {'from': str(start), 'to': str(end), 'loaded': [], 'unresolved': [], 'failed': [],
              'calendar_verified': expected_dates is not None}
    try:
        if instruments:
            master = download_instruments(downloader)
            write_parquet(master, config.data_dir / 'normalized' / 'instruments'
                          / f'{master.snapshot_date.iloc[0]}.parquet')
        # Probe ALL calendar days by default: special weekend sessions must not be lost.
        days = sorted(expected_dates) if expected_dates is not None else (
            start + timedelta(days=offset) for offset in range((end - start).days + 1))
        for day in days:
            if not start <= day <= end:
                continue
            url = source_url(day)
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
            except (ValueError, OSError, BadZipFile, requests.RequestException) as error:
                report['failed'].append({'date': str(day), 'error': str(error)})
                print(f'{day}: failed {error}', flush=True)
    except Exception as error:
        report['failed'].append({'stage': 'bootstrap', 'error': str(error)})
        raise
    finally:
        downloader.close()
        total = sum(len(report[key]) for key in ('loaded', 'failed', 'unresolved'))
        report['coverage'] = len(report['loaded']) / total if total and expected_dates is not None else None
        report['status'] = ('FAILED' if report['failed'] else
                            'INCOMPLETE' if report['unresolved'] or not report['loaded'] else 'SUCCESS')
        path = config.data_dir / 'reports' / f'bootstrap-{start}-{end}.json'
        atomic_write(path, json.dumps(report, indent=2).encode())
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--from', dest='start', type=date.fromisoformat, default=date(2018, 1, 1))
    parser.add_argument('--to', dest='end', type=date.fromisoformat,
                        default=datetime.now(ZoneInfo('Asia/Kolkata')).date() - timedelta(days=1))
    parser.add_argument('--data-dir', type=Path)
    parser.add_argument('--skip-instruments', action='store_true')
    parser.add_argument('--trading-dates', type=Path,
                        help='Verified session calendar: one ISO date per line, including special sessions')
    args = parser.parse_args()
    if args.start > args.end:
        parser.error('--from must not be after --to')
    expected = None
    if args.trading_dates:
        expected = {date.fromisoformat(line.strip()) for line in args.trading_dates.read_text().splitlines()
                    if line.strip()}
        if not any(args.start <= day <= args.end for day in expected):
            parser.error('Trading calendar contains no dates in requested range')
    config = Config(data_dir=args.data_dir) if args.data_dir else Config()
    report = run(config, args.start, args.end, instruments=not args.skip_instruments,
                 expected_dates=expected)
    print(json.dumps(report, indent=2))
    return 0 if report['status'] == 'SUCCESS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
