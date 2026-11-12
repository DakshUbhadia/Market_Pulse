"""Archive corporate records in overlap windows, preserving every filing version."""
import json
from datetime import timedelta

import pandas as pd

from quant.data import nse_corporate_actions, nse_financials, nse_shareholding, nse_announcements
from quant.data.http import atomic_write
from quant.data.normalization import write_observation
from quant.data.nse_client import NseClient, NseSourceError
from quant.data.security_history import resolve_identity
from quant.data.shareholding_xbrl import parse_shareholding_xbrl
from quant.data.xbrl import extract_financials
from quant.pipeline.state import PipelineState


def windows(start, end, days=30):
    while start <= end:
        stop = min(end, start + timedelta(days=days - 1))
        yield start, stop
        start = stop + timedelta(days=1)


def archive_filings(client, frame, dataset, history):
    review = []
    for i, row in frame.iterrows():
        if not row.get('instrument_id'):
            day = row.get('period_end') if dataset == 'financials' else row.get('as_on_date')
            frame.loc[i, 'instrument_id'] = resolve_identity(history, row.symbol, day)
        document = row.get('source_document')
        if not document:
            review.append({'filing_id': row.filing_id, 'reason': 'NO_XBRL_DOCUMENT'})
            frame.loc[i, 'parser_status'] = 'NEEDS_REVIEW'
            continue
        try:
            content = client.get_bytes(document, dataset='financial_xbrl' if dataset == 'financials'
                                       else 'shareholding_xbrl', suffix='xml')
            raw = client.last_response
            frame.loc[i, 'document_sha256'] = raw.sha256
            frame.loc[i, 'document_raw_path'] = str(raw.path)
            if dataset == 'financials':
                if pd.isna(row.get('bank')) or row.standalone_or_consolidated not in ('Consolidated', 'Non-Consolidated', 'Standalone'):
                    raise ValueError('Unknown financial institution type or consolidation basis')
                start = row.get('period_start')
                values = extract_financials(content, row.period_end,
                    consolidated=row.standalone_or_consolidated == 'Consolidated',
                    bank=bool(row.get('bank')), period_start=start if pd.notna(start) else None)
            else:
                values = parse_shareholding_xbrl(content, row.as_on_date)
                values['parser_status'] = 'PARSED' if any(value is not None for value in values.values()) else 'NEEDS_REVIEW'
            for key, value in values.items():
                frame.loc[i, key] = value
            if values['parser_status'] != 'PARSED':
                review.append({'filing_id': row.filing_id, 'reason': 'UNSUPPORTED_CONTEXT_OR_TAXONOMY'})
            if dataset == 'financials' and row.get('timing_status') != 'VERIFIED':
                review.append({'filing_id': row.filing_id, 'reason': 'UNCERTAIN_DISSEMINATION_TIME'})
            if pd.isna(frame.loc[i, 'instrument_id']):
                review.append({'filing_id': row.filing_id, 'reason': 'UNRESOLVED_IDENTITY'})
        except (ValueError, OSError, NseSourceError) as error:
            review.append({'filing_id': row.filing_id, 'reason': str(error)})
            frame.loc[i, 'parser_status'] = 'NEEDS_REVIEW'
    return frame, review


def update_corporate(config, start, end):
    state = PipelineState(config)
    path = config.data_dir / 'normalized' / 'security_history' / 'identities.parquet'
    history = pd.read_parquet(path) if path.exists() else pd.DataFrame()
    report = {}
    sources = [('corporate_actions', True, nse_corporate_actions, nse_corporate_actions.parse_corporate_actions),
               ('financials', config.enable_fundamentals, nse_financials, nse_financials.parse_financial_filings),
               ('shareholding', config.enable_shareholding, nse_shareholding, nse_shareholding.parse_shareholding),
               ('announcements', config.enable_announcements, nse_announcements, nse_announcements.parse_announcements)]
    with NseClient(config) as client:
        for name, enabled, adapter, parse in sources:
            key = 'nse_' + name
            if not enabled:
                report[key] = {'status': 'DISABLED'}
                state.record(key, status='DISABLED')
                continue
            # The document requires validated EOD history before financial parsing.
            if name == 'financials':
                from quant.pipeline.audit_prices import audit_prices
                try:
                    adjusted = state.data.get('adjusted_prices', {})
                    if (adjusted.get('status') != 'READY' or adjusted.get('from', '9999-12-31') > str(start)
                            or adjusted.get('to', '') < str(end)):
                        raise ValueError('Adjusted-price foundation must be validated before financial ingestion')
                    if audit_prices(config, start, end)['status'] != 'READY':
                        raise ValueError('Price foundation must pass audit before financial ingestion')
                except (ValueError, OSError) as error:
                    report[key] = {'status': 'FAILED', 'error': str(error)}
                    state.record(key, **report[key])
                    continue
            first = state.overlap_start(key, start, end)
            coverage_start = min(str(start), state.data.get(key, {}).get('checked_from', str(start)))
            count, usable_filings, reviews, completed = 0, 0, [], []
            try:
                for begin, stop in windows(first, end):
                    for period in (('Quarterly', 'Annual') if name == 'financials' else (None,)):
                        params = {'index': 'equities', 'from_date': begin.strftime('%d-%m-%Y'),
                                  'to_date': stop.strftime('%d-%m-%Y')}
                        if period:
                            params['period'] = period
                        payload = client.get_json(adapter.PATH, params=params,
                            dataset='financial_filings' if name == 'financials' else name)
                        raw = client.last_response
                        frame = parse(payload, raw, history) if name == 'corporate_actions' else parse(payload, raw)
                        if name == 'corporate_actions' and not frame.empty:
                            reviews.extend({'event_id': row.event_id, 'symbol': row.symbol,
                                            'reason': 'AMBIGUOUS_ACTION' if row.parse_status not in ('PARSED', 'NON_ADJUSTING') else 'UNRESOLVED_IDENTITY'}
                                           for row in frame.itertuples()
                                           if row.parse_status not in ('PARSED', 'NON_ADJUSTING') or pd.isna(row.instrument_id))
                        if name in ('financials', 'shareholding') and not frame.empty:
                            frame, needs_review = archive_filings(client, frame, name, history)
                            reviews.extend(needs_review)
                            usable_filings += int(((frame.parser_status == 'PARSED')
                                & (frame.timing_status == 'VERIFIED') & frame.instrument_id.notna()).sum())
                        write_observation(frame, config.data_dir / 'normalized' / name, raw.sha256, raw.fetched_at)
                        count += len(frame)
                    completed.append(str(stop))
                    state.record(key, status='READY', checked_through=str(stop), checked_from=coverage_start)
                report[key] = {'status': 'READY', 'records_seen': count, 'checked_through': str(end),
                                'checked_from': state.data[key].get('checked_from', str(start)),
                                'needs_review': reviews, 'usable_filings': usable_filings}
            except (NseSourceError, ValueError, OSError) as error:
                report[key] = {'status': 'FAILED', 'error': str(error), 'completed_windows': completed,
                                'needs_review': reviews}
            state.record(key, **report[key])
    atomic_write(config.data_dir / 'reports' / f'corporate-{end}.json', json.dumps(report, indent=2).encode())
    return report


def main():
    from quant.pipeline.cli import parser_config
    parser, config = parser_config(__doc__)
    args = parser.parse_args()
    report = update_corporate(args.config(config), args.start, args.end)
    print(json.dumps(report, indent=2))
    return 0 if all(row['status'] in ('READY', 'DISABLED') for row in report.values()) else 1


if __name__ == '__main__':
    raise SystemExit(main())
