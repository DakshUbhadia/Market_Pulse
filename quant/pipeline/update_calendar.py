"""Automatically refresh NSE calendar; failed refreshes retain the last valid data."""
import argparse
import json
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo
from zipfile import BadZipFile

import pandas as pd
import requests

from quant.config import Config
from quant.data.http import Downloader, atomic_write, sha256
from quant.data.nse_bhavcopy import parse_bhavcopy, source_url
from quant.data.nse_calendar import (HOLIDAY_PATH, HOLIDAY_PAGE, build_calendar, calendar_report,
                                    loaded_bhavcopy_evidence, parse_holidays, parse_muhurat_notice)
from quant.data.nse_client import NseClient, NseSourceError
from quant.storage.parquet_store import write_parquet, write_prices


def confirm_special_sessions(config, events, start, end):
    """Resolve past ambiguous festival dates using the actual official price archive."""
    observations, _ = loaded_bhavcopy_evidence(config, start, end)
    today = datetime.now(ZoneInfo(config.timezone)).date()
    downloader = Downloader(config)
    failures = []
    try:
        for entries in events.values():
            for day, event in entries.items():
                if (not start <= day <= end or day >= today or day in observations
                        or event['investigation_reason'] != 'MUHURAT_REQUIRES_CONFIRMATION'):
                    continue
                url = source_url(day, config.nse_archives_url)
                path = config.data_dir / 'raw' / 'nse' / str(day.year) / url.rsplit('/', 1)[-1]
                try:
                    frame = parse_bhavcopy(downloader.fetch(url, path), day, url)
                    write_prices(frame, config.prices_dir)
                except (ValueError, OSError, BadZipFile, requests.RequestException) as error:
                    failures.append({'date': str(day), 'error': str(error)})
    finally:
        downloader.close()
    return failures


def persist_calendar(config, frame, report):
    # The Parquet file is authoritative; exports carry its digest to detect a partial write.
    write_parquet(frame, config.calendar_path)
    content = ''.join(f'{day.date()}\n' for day in frame.loc[frame.is_trading_session, 'trade_date']).encode()
    atomic_write(config.calendar_text_path, content)
    metadata = {'from': report['from'], 'to': report['to'],
                'calendar_sha256': sha256(config.calendar_path.read_bytes()),
                'sha256': sha256(content), 'status': report['status'], 'generated': True}
    atomic_write(config.calendar_text_path.with_suffix('.txt.json'), json.dumps(metadata, indent=2).encode())


def refresh_calendar(config: Config, start: date, end: date, *, client=None):
    if start > end:
        raise ValueError('Calendar start must not be after end')
    # Preserve previously covered years when a scheduled update requests a shorter range.
    if config.calendar_path.exists():
        previous = pd.read_parquet(config.calendar_path, columns=['trade_date'])
        if not previous.empty:
            start = min(start, previous.trade_date.min().date())
            end = max(end, previous.trade_date.max().date())
    report_path = config.data_dir / 'reports' / 'calendar-health.json'
    owned = client is None
    client = client or NseClient(config)
    checked_at = datetime.now(ZoneInfo(config.timezone)).isoformat()
    try:
        events, sources = {}, {}
        for year in range(start.year, end.year + 1):
            payload = client.get_json(HOLIDAY_PATH, params={'type': 'trading', 'year': year},
                                      referer=config.nse_base_url + HOLIDAY_PAGE, dataset='calendar')
            sources[year] = client.last_response
            events[year] = parse_holidays(payload, year, client.last_response)
        notice = client.get_bytes(HOLIDAY_PAGE, dataset='calendar', suffix='html')
        specials = parse_muhurat_notice(notice, client.last_response)
        special_checks = confirm_special_sessions(config, events, start, end)
        observations, invalid = loaded_bhavcopy_evidence(config, start, end)
        frame = build_calendar(start, end, events, sources, special_events=specials,
                               observed=observations, normalized_at=checked_at)
        report = calendar_report(frame, invalid_partitions=invalid)
        report['checked_at'] = checked_at
        report['special_session_check_failures'] = special_checks
        persist_calendar(config, frame, report)
        atomic_write(report_path, json.dumps(report, indent=2).encode())
        return frame, report
    except Exception as error:
        atomic_write(report_path, json.dumps({'status': 'FAILED', 'checked_at': checked_at,
                     'error': str(error), 'prior_calendar_retained': config.calendar_path.exists()}, indent=2).encode())
        raise
    finally:
        if owned:
            client.close()


def read_calendar(config: Config, start: date, end: date):
    health_path = config.data_dir / 'reports' / 'calendar-health.json'
    if health_path.exists() and json.loads(health_path.read_text())['status'] == 'FAILED':
        raise ValueError('Last calendar refresh failed; refresh successfully before backfilling')
    frame = pd.read_parquet(config.calendar_path)
    frame = frame[(frame.trade_date.dt.date >= start) & (frame.trade_date.dt.date <= end)].copy()
    if len(frame) != (end - start).days + 1 or frame.trade_date.duplicated().any():
        raise ValueError('Generated calendar does not cover the requested date range')
    if frame.needs_investigation.any():
        raise ValueError('Calendar has unresolved session investigations; inspect calendar-health.json')
    return frame


def reconcile_calendar(config: Config, start: date, end: date):
    """Reconcile after ingestion without another web request."""
    frame = pd.read_parquet(config.calendar_path)
    observations, invalid = loaded_bhavcopy_evidence(config, start, end)
    selected = frame.trade_date.dt.date.between(start, end)
    # Do not retain prior successful verification when a partition is now missing/corrupt.
    frame.loc[selected, 'verified'] = False
    frame.loc[selected, 'observed_source_url'] = None
    frame.loc[selected, 'observed_raw_sha256'] = None
    frame.loc[selected & (frame.verification == 'BHAVCOPY'), 'verification'] = 'CALENDAR_RULE'
    for i, row in frame.loc[selected].iterrows():
        day = row.trade_date.date()
        if day in observations:
            if not row.is_trading_session:
                frame.loc[i, ['needs_investigation', 'investigation_reason']] = [True, 'BHAVCOPY_ON_EXCLUDED_DATE']
                frame.loc[i, 'session_type'] = 'SPECIAL'
            frame.loc[i, ['is_trading_session', 'verified', 'verification']] = [True, True, 'BHAVCOPY']
            frame.loc[i, 'observed_source_url'] = observations[day]['source_url']
            frame.loc[i, 'observed_raw_sha256'] = observations[day]['raw_sha256']
    report = calendar_report(frame, invalid_partitions=invalid)
    report['checked_at'] = datetime.now(ZoneInfo(config.timezone)).isoformat()
    persist_calendar(config, frame, report)
    atomic_write(config.data_dir / 'reports' / 'calendar-health.json', json.dumps(report, indent=2).encode())
    return report


def main():
    config = Config()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--from', dest='start', type=date.fromisoformat, default=date(2018, 1, 1))
    parser.add_argument('--to', dest='end', type=date.fromisoformat,
                        default=datetime.now(ZoneInfo(config.timezone)).date() - timedelta(days=1))
    parser.add_argument('--data-dir', type=Path)
    args = parser.parse_args()
    if args.start > args.end:
        parser.error('--from must not be after --to')
    if args.data_dir:
        from dataclasses import replace
        config = replace(config, data_dir=args.data_dir)
    try:
        _, report = refresh_calendar(config, args.start, args.end)
    except (NseSourceError, ValueError, OSError) as error:
        print(f'Calendar update failed: {error}')
        return 1
    print(json.dumps({key: value for key, value in report.items() if key != 'unverified_sessions'}, indent=2))
    return 0 if report['status'] == 'READY' else 1


if __name__ == '__main__':
    raise SystemExit(main())
