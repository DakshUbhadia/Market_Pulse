"""Cash-market calendar derived from exchange records and observed bhavcopies."""
import json
import re
from datetime import date, datetime
from html.parser import HTMLParser

import pandas as pd

from quant.data.nse_bhavcopy import validate_bars
from quant.data.nse_client import NseSourceError, RawResponse

PARSER_VERSION = '1.0.0'
HOLIDAY_PATH = '/api/holiday-master'
HOLIDAY_PAGE = '/resources/exchange-communication-holidays'


def exchange_date(value: str) -> date:
    # Avoid locale-dependent %b parsing on machines without English date settings.
    months = {month: i + 1 for i, month in enumerate(
        ('jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec'))}
    try:
        day, month, year = value.strip().split('-')
        return date(int(year), months[month.lower()], int(day))
    except (ValueError, KeyError, AttributeError):
        raise ValueError('Invalid NSE calendar date') from None


def parse_holidays(payload, year: int, raw: RawResponse) -> dict[date, dict]:
    """Require the CM segment and requested year; never reuse another year's list."""
    if not isinstance(payload, dict) or not isinstance(payload.get('CM'), list) or not payload['CM']:
        raise NseSourceError(f'NSE returned no cash-market holiday calendar for {year}')
    events = {}
    for item in payload['CM']:
        if not isinstance(item, dict) or not isinstance(item.get('description'), str):
            raise NseSourceError('NSE holiday schema changed')
        try:
            day = exchange_date(item.get('tradingDate'))
        except ValueError as error:
            raise NseSourceError(str(error)) from None
        if day.year != year:
            raise NseSourceError(f'NSE returned a different year for requested calendar {year}')
        description = ' '.join(item['description'].split())
        if not description:
            raise NseSourceError('NSE holiday description is empty')
        text = description.lower()
        special = 'special live trading' in text or 'special trading session' in text
        muhurat = bool(re.search(r'muh[au]rat', text)) and 'trading' in text
        # A holiday caption alone does not prove that a special session took place.
        ambiguous = ('diwali' in text and ('laxmi' in text or 'lakshmi' in text)) and not muhurat
        event = {
            'is_trading_session': special or muhurat,
            'session_type': 'MUHURAT' if muhurat else 'SPECIAL' if special else 'NORMAL',
            'description': description, 'needs_investigation': ambiguous,
            'investigation_reason': 'MUHURAT_REQUIRES_CONFIRMATION' if ambiguous else '',
            **raw.provenance(),
        }
        if day in events and events[day] != event:
            raise NseSourceError(f'Conflicting NSE calendar entries for {day}')
        events[day] = event
    return events


class _Text(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []

    def handle_data(self, data):
        self.parts.append(data)


def parse_muhurat_notice(content: bytes, raw: RawResponse) -> dict[date, dict]:
    """Parse only explicit dated NSE notices; a festival name is not a session."""
    parser = _Text()
    parser.feed(content.decode('utf-8'))
    text = ' '.join(' '.join(parser.parts).split())
    pattern = (r'Muhurat Trading (?:will be|shall be|was) conducted on '
               r'(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday),? '
               r'([A-Za-z]+) (\d{1,2}),? (\d{4})')
    events = {}
    for month, day, year in re.findall(pattern, text, flags=re.I):
        day = exchange_date(f'{day}-{month[:3]}-{year}')
        events[day] = {'is_trading_session': True, 'session_type': 'MUHURAT',
                       'description': 'Dated NSE Muhurat trading notice',
                       'needs_investigation': False, 'investigation_reason': '', **raw.provenance()}
    return events


def loaded_bhavcopy_evidence(config, start: date, end: date):
    """Inspect partition contents, not filenames alone. Corrupt partitions stay flagged."""
    observations, invalid = {}, []
    for path in sorted(config.prices_dir.glob('year=*/month=*/*.parquet')):
        try:
            # Filename only selects candidates. Contents establish successful observations.
            candidate = date.fromisoformat(path.stem)
            if not start <= candidate <= end:
                continue
            frame = pd.read_parquet(path)
            validate_bars(frame)
            dates = pd.to_datetime(frame.trade_date).dt.date.unique()
            hashes = frame.source_hash.unique()
            urls = frame.source_file.unique()
            if (len(dates) != 1 or dates[0] != candidate or len(hashes) != 1 or len(urls) != 1
                    or not re.fullmatch(r'[a-f0-9]{64}', str(hashes[0]))):
                raise ValueError('Invalid partition date or provenance')
            observations[candidate] = {'source_url': urls[0], 'raw_sha256': hashes[0], 'rows': len(frame)}
        except (ValueError, OSError, KeyError, TypeError) as error:
            invalid.append({'partition': str(path), 'error': str(error)})
    return observations, invalid


def build_calendar(start: date, end: date, year_events: dict, year_sources: dict,
                   *, special_events=None, observed=None, normalized_at: str) -> pd.DataFrame:
    if start > end:
        raise ValueError('Calendar start must not be after end')
    if any(year not in year_events or year not in year_sources for year in range(start.year, end.year + 1)):
        raise ValueError('Calendar does not cover all requested years')
    observed = observed or {}
    special_events = special_events or {}
    rows = []
    for timestamp in pd.date_range(start, end, freq='D'):
        day = timestamp.date()
        source = year_sources[day.year]
        row = {'trade_date': timestamp, 'is_trading_session': day.weekday() < 5,
               'session_type': 'NORMAL', 'description': 'Weekday schedule' if day.weekday() < 5 else 'Weekend',
               'needs_investigation': False, 'investigation_reason': '',
               'verified': False, 'verification': 'CALENDAR_RULE', **source.provenance()}
        event = year_events[day.year].get(day)
        if event:
            row.update(event)
            row['verification'] = 'EXCHANGE_NOTICE'
        if day in special_events:
            row.update(special_events[day])
            row['verification'] = 'EXCHANGE_NOTICE'
        row['calendar_source_url'] = row['source_url']
        row['calendar_raw_sha256'] = row['raw_sha256']
        row['observed_source_url'] = None
        row['observed_raw_sha256'] = None
        if day in observed:
            if not row['is_trading_session']:
                # Bhavcopy is evidence of trading; retain disagreement for later review.
                muhurat = row['investigation_reason'] == 'MUHURAT_REQUIRES_CONFIRMATION'
                row['needs_investigation'] = not muhurat
                row['investigation_reason'] = '' if muhurat else 'BHAVCOPY_ON_EXCLUDED_DATE'
                row['session_type'] = 'MUHURAT' if muhurat else 'SPECIAL'
            row['is_trading_session'] = True
            row['verified'] = True
            row['verification'] = 'BHAVCOPY'
            row['observed_source_url'] = observed[day]['source_url']
            row['observed_raw_sha256'] = observed[day]['raw_sha256']
        row.update(source_asof=row['fetched_at'], parser_version=PARSER_VERSION, normalized_at=normalized_at)
        rows.append(row)
    frame = pd.DataFrame(rows)
    for column in ('source_asof', 'fetched_at', 'normalized_at'):
        frame[column] = pd.to_datetime(frame[column], utc=True)
    return frame


def calendar_report(frame: pd.DataFrame, *, invalid_partitions=None):
    expected = frame[frame.is_trading_session]
    verified = expected[expected.verified]
    flagged = frame[frame.needs_investigation]
    return {
        'from': frame.trade_date.min().date().isoformat(),
        'to': frame.trade_date.max().date().isoformat(),
        'status': 'NEEDS_REVIEW' if len(flagged) or invalid_partitions else 'READY',
        'expected_sessions': len(expected), 'verified_price_sessions': len(verified),
        'observed_price_coverage': len(verified) / len(expected) if len(expected) else None,
        'unverified_sessions': [str(day.date()) for day in expected.loc[~expected.verified, 'trade_date']],
        'investigations': [{'date': str(row.trade_date.date()), 'reason': row.investigation_reason}
                           for row in flagged.itertuples()],
        'invalid_partitions': invalid_partitions or [],
        'calendar_basis': 'NSE CM holiday lists + explicit special notices + validated local bhavcopies',
        'limitation': 'Unlisted special sessions require archive reconciliation; coverage is against this source-derived calendar.',
    }
