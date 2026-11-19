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
    if attempt.get('parser_status') in ('SUPPORTED_BUT_NO_REQUIRED_FACT', 'NO_REQUIRED_FACT'):
        return 'SUPPORTED_BUT_NO_REQUIRED_FACT', False
    if 'ENTITY' in reasons and 'UNRESOLVED_IDENTITY' not in reasons:
        return 'UNSUPPORTED_ENTITY', False
    if any(token in reasons for token in ('TAXONOMY', 'NO_XBRL_DOCUMENT', 'UNSUPPORTED_DOCUMENT')):
        return 'UNSUPPORTED_DOCUMENT', False
    if attempt.get('parser_status') == 'SUPPORTED_BUT_NO_REQUIRED_FACT':
        return 'SUPPORTED_BUT_NO_REQUIRED_FACT', False
    return 'NEEDS_REVIEW', False


TERMINAL_STATES = {'PARSED', 'NO_REQUIRED_FACT', 'UNSUPPORTED_ENTITY', 'UNSUPPORTED_DOCUMENT',
                   'PERMANENT_REVIEW', 'RETRYABLE_EXHAUSTED', 'MISSING_SOURCE_URL'}


def terminal_status(status, retryable, source_document, attempt=None):
    if status == 'PARSED':
        return 'PARSED'
    if not isinstance(source_document, str) or not source_document.strip():
        return 'MISSING_SOURCE_URL'
    if retryable:
        exhaustion = (attempt or {}).get('retry_exhaustion', {})
        reviewed = pd.to_datetime(exhaustion.get('reviewed_at'), utc=True, errors='coerce')
        if (exhaustion.get('reviewed_by') and exhaustion.get('reason') and pd.notna(reviewed)
                and reviewed <= pd.Timestamp.now(tz='UTC')
                and type(exhaustion.get('max_attempts')) is int and exhaustion['max_attempts'] > 0
                and type((attempt or {}).get('attempt_count')) is int
                and attempt['attempt_count'] >= exhaustion['max_attempts']):
            return 'RETRYABLE_EXHAUSTED'
        return 'RETRYABLE_FAILURE'
    if status == 'NEEDS_REVIEW':
        review = (attempt or {}).get('permanent_review', {})
        reviewed = pd.to_datetime(review.get('reviewed_at'), utc=True, errors='coerce')
        return ('PERMANENT_REVIEW' if review.get('reviewed_by') and review.get('reason')
                and pd.notna(reviewed) and reviewed <= pd.Timestamp.now(tz='UTC') else 'NEEDS_REVIEW')
    return {'SUPPORTED_BUT_NO_REQUIRED_FACT': 'NO_REQUIRED_FACT',
            }.get(status, status)


def acquisition_report(filings, attempts, *, start, end, candidate_set=None):
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
    from quant.forward.signal_store import content_hash
    declared = sorted(candidate_set if candidate_set is not None else frame.get('candidate_id', []))
    if len(declared) != len(set(declared)):
        raise ValueError('Stage candidate set contains duplicate identities')
    if candidate_set is not None:
        if not set(declared).issubset(set(frame.get('candidate_id', []))):
            raise ValueError('Declared Stage 1 candidates disappeared from acquisition metadata')
        frame = frame[frame.candidate_id.isin(declared)] if len(frame) else frame
    details = []
    for row in frame.to_dict('records'):
        key = row['candidate_id']
        attempt = attempts.get(key) or attempts.get(row['filing_id'])
        if attempt is None and isinstance(row.get('document_sha256'), str):
            attempt = dict(parser_status=row.get('parser_status'), document_sha256=row['document_sha256'], review=[])
        status, retry = classify_attempt(attempt) if attempt is not None else ('UNATTEMPTED', False)
        terminal = terminal_status(status, retry, row.get('source_document'), attempt)
        details.append(dict(filing_id=key, status=status, retryable=retry, attempted=attempt is not None,
            terminal_status=terminal, instrument_id=row.get('instrument_id'),
            source_document=row.get('source_document'),
            downloaded=bool(attempt and isinstance(attempt.get('document_sha256'), str)),
            timing_verified=row.get('timing_status') == 'VERIFIED',
            identity_resolved=isinstance(row.get('instrument_id'), str) and bool(row['instrument_id']),
            entity_type=str(row.get('entity_type') or row.get('financial_schema') or 'UNKNOWN'),
            period_type=str(row.get('period_type') or 'UNKNOWN'),
            year=str(pd.Timestamp(row['exchange_disseminated_at']).year) if pd.notna(row['exchange_disseminated_at']) else 'UNKNOWN_PIT_TIMESTAMP',
            taxonomy=str((attempt or {}).get('taxonomy') or 'UNASSESSED')))
    attempted = sum(r['attempted'] for r in details)
    parsed = sum(r['status'] == 'PARSED' for r in details)
    usable = sum(r['status'] == 'PARSED' and r['downloaded'] and r['timing_verified'] and r['identity_resolved'] for r in details)
    review = sum(r['attempted'] and r['status'] != 'PARSED' and not r['retryable'] for r in details)
    total = len(details)
    terminal_count = sum(r['terminal_status'] in TERMINAL_STATES for r in details)
    unattempted_scope = sum(not r['attempted'] and r['terminal_status'] != 'MISSING_SOURCE_URL' for r in details)
    result = dict(candidate_documents=total, attempted=attempted, downloaded=sum(r['downloaded'] for r in details),
        parsed=parsed, needs_review=review, permanent_failures=review,
        retryable_failures=sum(r['retryable'] for r in details), unattempted=total-attempted,
        completion_pct=100*attempted/total if total else None,
        parse_success_pct=100*parsed/attempted if attempted else None,
        timing_verified_pct=100*sum(r['timing_verified'] for r in details if r['attempted'])/attempted if attempted else None,
        identity_resolved_pct=100*sum(r['identity_resolved'] for r in details if r['attempted'])/attempted if attempted else None,
        candidate_count=total, attempted_count=attempted, terminal_status_count=terminal_count,
        retryable_count=sum(r['retryable'] for r in details), unattempted_count=total-attempted,
        attempt_completion_pct=100*attempted/total if total else None,
        usable_document_count=usable, usable_document_pct=100*usable/total if total else None,
        usable_document_scope='PARSED_WITH_VERIFIED_TIMING_AND_IDENTITY_NOT_UNIVERSE_CERTIFICATION',
        terminal_status_counts=dict(Counter(r['terminal_status'] for r in details)),
        declared_candidate_ids=declared, candidate_set_sha256=content_hash(declared),
        unattempted_in_scope=unattempted_scope, stage1_complete=bool(total and total == terminal_count and unattempted_scope == 0),
        status='ALL_CANDIDATES_CLASSIFIED' if total and total == terminal_count else 'INCOMPLETE',
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
    declaration = config.data_dir/'state/fundamental_backfill'/f'stage1-candidates-{start}-{end}.json'
    declared = None
    if declaration.exists():
        from quant.forward.signal_store import content_hash
        frozen = json.loads(declaration.read_text(encoding='utf-8'))
        if frozen.get('sha256') != content_hash({k: v for k, v in frozen.items() if k != 'sha256'}):
            raise ValueError('Stage 1 candidate declaration checksum changed')
        declared = frozen['candidate_ids']
    report = acquisition_report(frame, attempts, start=start, end=end, candidate_set=declared)
    report['candidate_scope'] = 'FROZEN_STAGE1_SET' if declared is not None else 'CURRENT_DISCOVERY_SNAPSHOT'
    report['input_sha256'] = {str(p): digest_file(p) for p in [*paths, *([checkpoint] if checkpoint.exists() else [])]}
    if declaration.exists():
        report['input_sha256'][str(declaration)] = digest_file(declaration)
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
