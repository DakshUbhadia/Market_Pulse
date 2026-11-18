"""Classify every discovered candidate, including unattempted documents."""
from collections import Counter
import json
import pandas as pd

from quant.storage.parquet_store import read_parquet_file
from quant.storage.research_store import digest_file, write_json


def classify_attempt(attempt):
    reviews = attempt.get('review', [])
    reasons = ' '.join(str(r.get('reason', '')) for r in reviews).upper()
    if any(r.get('source_status') == 'LIVE_SOURCE_UNAVAILABLE' for r in reviews) or any(
            token in reasons for token in ('HTTP 403', 'HTTP 429', 'HTTP 5', 'NETWORK', 'TIMEOUT', 'CONNECTION')):
        return 'DOWNLOAD_FAILED', True
    if attempt.get('parser_status') == 'PARSED':
        return ('NEEDS_REVIEW', False) if reviews else ('PARSED', False)
    if 'ENTITY' in reasons and 'UNRESOLVED_IDENTITY' not in reasons:
        return 'UNSUPPORTED_ENTITY', False
    if any(token in reasons for token in ('TAXONOMY', 'NO_XBRL_DOCUMENT', 'UNSUPPORTED_DOCUMENT')):
        return 'UNSUPPORTED_DOCUMENT', False
    if attempt.get('parser_status') == 'SUPPORTED_BUT_NO_REQUIRED_FACT':
        return 'SUPPORTED_BUT_NO_REQUIRED_FACT', False
    return 'NEEDS_REVIEW', False


def acquisition_report(filings, attempts, *, start, end):
    frame = filings.copy()
    if not frame.empty:
        stamps = pd.to_datetime(frame.exchange_disseminated_at, utc=True, errors='coerce')
        frame = frame[stamps.isna() | (stamps.ge(pd.Timestamp(start, tz='Asia/Kolkata'))
                      & stamps.lt(pd.Timestamp(end, tz='Asia/Kolkata')+pd.Timedelta(days=1)))]
        # A parsed version and its metadata candidate are one document candidate.
        frame['candidate_id'] = frame.get('metadata_filing_id', frame.filing_id).fillna(frame.filing_id)
        if 'first_seen_at' in frame:
            frame = frame.sort_values('first_seen_at')
        frame = frame.drop_duplicates('candidate_id', keep='last')
    details = []
    for row in frame.to_dict('records'):
        key = row['candidate_id']
        attempt = attempts.get(key) or attempts.get(row['filing_id'])
        if attempt is None and isinstance(row.get('document_sha256'), str):
            attempt = dict(parser_status=row.get('parser_status'), document_sha256=row['document_sha256'], review=[])
        status, retry = classify_attempt(attempt) if attempt is not None else ('UNATTEMPTED', False)
        details.append(dict(filing_id=key, status=status, retryable=retry, attempted=attempt is not None,
            downloaded=bool(attempt and isinstance(attempt.get('document_sha256'), str)),
            timing_verified=row.get('timing_status') == 'VERIFIED',
            identity_resolved=isinstance(row.get('instrument_id'), str) and bool(row['instrument_id']),
            entity_type=str(row.get('entity_type') or row.get('financial_schema') or 'UNKNOWN'),
            period_type=str(row.get('period_type') or 'UNKNOWN'),
            year=str(pd.Timestamp(row['exchange_disseminated_at']).year) if pd.notna(row['exchange_disseminated_at']) else 'UNKNOWN_PIT_TIMESTAMP',
            taxonomy=str((attempt or {}).get('taxonomy') or 'UNASSESSED')))
    attempted = sum(r['attempted'] for r in details)
    parsed = sum(r['status'] == 'PARSED' for r in details)
    review = sum(r['attempted'] and r['status'] != 'PARSED' and not r['retryable'] for r in details)
    total = len(details)
    result = dict(candidate_documents=total, attempted=attempted, downloaded=sum(r['downloaded'] for r in details),
        parsed=parsed, needs_review=review, permanent_failures=review,
        retryable_failures=sum(r['retryable'] for r in details), unattempted=total-attempted,
        completion_pct=100*attempted/total if total else None,
        parse_success_pct=100*parsed/attempted if attempted else None,
        timing_verified_pct=100*sum(r['timing_verified'] for r in details if r['attempted'])/attempted if attempted else None,
        identity_resolved_pct=100*sum(r['identity_resolved'] for r in details if r['attempted'])/attempted if attempted else None,
        status='ALL_CANDIDATES_CLASSIFIED' if total and total == attempted else 'INCOMPLETE',
        factor_v2_enabled=False, coverage_certified=False, details=details)
    for dimension in ('entity_type', 'period_type', 'year', 'taxonomy'):
        groups = {}
        for row in details:
            group = groups.setdefault(row[dimension], Counter())
            group['candidate_documents'] += 1
            group[row['status']] += 1
        result['by_'+dimension] = {k: dict(v) for k, v in groups.items()}
    return result


def report_fundamental_acquisition(config, start, end):
    paths = sorted((config.data_dir/'normalized/financials').rglob('*.parquet'))
    frame = pd.concat([read_parquet_file(p) for p in paths], ignore_index=True) if paths else pd.DataFrame()
    checkpoint = config.data_dir/'state/fundamental_backfill'/f'documents-{start}-{end}.json'
    attempts = json.loads(checkpoint.read_text(encoding='utf-8')).get('attempted', {}) if checkpoint.exists() else {}
    report = acquisition_report(frame, attempts, start=start, end=end)
    report['input_sha256'] = {str(p): digest_file(p) for p in [*paths, *([checkpoint] if checkpoint.exists() else [])]}
    write_json(config.data_dir/'reports/fundamental-acquisition.json', report)
    return report


def main():
    from quant.pipeline.cli import parser_config
    parser, config = parser_config(__doc__)
    args = parser.parse_args()
    report = report_fundamental_acquisition(args.config(config), args.start, args.end)
    print(json.dumps({k: v for k, v in report.items() if k != 'details'}, indent=2))
    return 0 if report['status'] == 'ALL_CANDIDATES_CLASSIFIED' else 1


if __name__ == '__main__':
    raise SystemExit(main())
