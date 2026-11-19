"""Predeclare a data-availability window without inspecting performance."""
from datetime import datetime, timezone
from pathlib import Path
import json

import pandas as pd

from quant.forward.signal_store import append_record, content_hash

EVALUATION_WINDOW_VERSION = 'validated_data_window_1.1.0'
SEARCH_STATES = {'EVIDENCE_SEARCH_ACTIVE', 'EVIDENCE_COMPLETE', 'EVIDENCE_EXHAUSTED_UNRESOLVED'}


def validate_search_audit(audit):
    if audit.get('status') not in SEARCH_STATES or not audit.get('event_id'):
        raise ValueError('Evidence search requires an event ID and explicit search status')
    if audit['status'] == 'EVIDENCE_EXHAUSTED_UNRESOLVED':
        required = ('sources_checked', 'dates_checked', 'documents_checked', 'search_completed_at',
                    'reason_transition_cannot_be_certified', 'reviewed_by', 'reviewed_at',
                    'missing_facts', 'evidence_hashes', 'conclusion')
        if any(not audit.get(key) for key in required):
            raise ValueError('Evidence exhaustion requires a completed, reviewed search audit')
        for key in ('sources_checked', 'dates_checked', 'documents_checked', 'missing_facts'):
            if not isinstance(audit[key], list) or any(not isinstance(v, str) or not v.strip() for v in audit[key]):
                raise ValueError('Evidence exhaustion requires explicit nonempty search audit lists')
        completed = pd.Timestamp(audit['search_completed_at'])
        if completed.tzinfo is None or completed > pd.Timestamp.now(tz='UTC'):
            raise ValueError('Evidence search completion must be a past timestamp with timezone')
        reviewed = pd.Timestamp(audit['reviewed_at'])
        if reviewed.tzinfo is None or reviewed < completed or reviewed > pd.Timestamp.now(tz='UTC'):
            raise ValueError('Evidence exhaustion review must follow search completion')
        import re
        hashes = audit['evidence_hashes']
        if not isinstance(hashes, dict) or any(not re.fullmatch('[0-9a-f]{64}', str(h)) for h in hashes.values()):
            raise ValueError('Evidence exhaustion requires document SHA-256 hashes')
        if audit.get('performance_used_to_choose_start') is not False:
            raise ValueError('Evidence exhaustion cannot be influenced by performance')
        if audit.get('performance_used_to_decide_exhaustion') is not False:
            raise ValueError('Evidence exhaustion must be decided independently of performance')
    return audit


def record_search_audit(audit, output, *, data_dir):
    """Archive a formal audit after checking referenced evidence bytes."""
    validate_search_audit(audit)
    from quant.storage.research_store import digest_file
    base = Path(data_dir).resolve()
    for name, expected in audit.get('evidence_hashes', {}).items():
        path = (base/name).resolve()
        if not path.is_relative_to(base) or not path.is_file() or digest_file(path) != expected:
            raise ValueError('Evidence search source is missing or its checksum changed')
    append_record(Path(output), dict(audit=audit, sha256=content_hash(audit)))


def select_evaluation_window(requested_start, sessions, blocking_events, *, warmup_sessions):
    if not isinstance(warmup_sessions, int) or warmup_sessions < 252:
        raise ValueError('Unchanged V1 feature warm-up requires at least 252 sessions')
    dates = pd.DatetimeIndex(pd.to_datetime(sessions))
    if dates.empty or dates.has_duplicates or dates.isna().any() or not dates.is_monotonic_increasing:
        raise ValueError('Ordered unique exchange sessions are required')
    start = pd.Timestamp(requested_start)
    blockers = [e for e in blocking_events if e.get('mandatory_held_event') is True]
    for event in blockers:
        validate_search_audit(event)
        if event['status'] != 'EVIDENCE_EXHAUSTED_UNRESOLVED':
            raise ValueError('A fallback window requires exhausted unresolved mandatory held-event evidence')
        if not event.get('boundary_date'):
            raise ValueError('Every blocker requires a dated evidence boundary')
    boundary = max((pd.Timestamp(e['boundary_date']) for e in blockers), default=None)
    candidates = dates[dates >= start]
    if boundary is not None:
        candidates = candidates[candidates > boundary]
        candidates = candidates[warmup_sessions:]
    if candidates.empty:
        raise ValueError('Insufficient certified sessions after the last boundary and feature warm-up')
    return dict(requested_start=str(start.date()), effective_start=str(candidates[0].date()),
        reason='EVIDENCE_AVAILABILITY_ONLY' if blockers else 'REQUESTED_WINDOW',
        blocking_event_ids=sorted(e['event_id'] for e in blockers), blocking_events=blockers,
        warmup_sessions=warmup_sessions, evidence_policy_version=EVALUATION_WINDOW_VERSION,
        selection_method='FIRST_SESSION_AFTER_LAST_MANDATORY_HELD_BOUNDARY_PLUS_WARMUP',
        performance_used_to_choose_start=False, original_baseline_status='BLOCKED' if blockers else 'UNCHANGED',
        declared_at=datetime.now(timezone.utc).isoformat(),
        selection_calendar=[d.isoformat() for d in dates],
        calendar_sha256=content_hash([d.isoformat() for d in dates]))


def freeze_evaluation_window(record, output):
    append_record(Path(output), dict(**record, sha256=content_hash(record)))


def load_evaluation_window(path):
    record = json.loads(Path(path).read_text(encoding='utf-8'))
    body = {k: v for k, v in record.items() if k != 'sha256'}
    if record.get('sha256') != content_hash(body):
        raise ValueError('Evaluation window checksum changed')
    if record.get('performance_used_to_choose_start') is not False:
        raise ValueError('Evaluation start cannot depend on performance')
    if record.get('evidence_policy_version') != EVALUATION_WINDOW_VERSION:
        raise ValueError('Unknown evaluation window policy')
    for event in record.get('blocking_events', []):
        validate_search_audit(event)
    expected = select_evaluation_window(record['requested_start'], record['selection_calendar'],
        record['blocking_events'], warmup_sessions=record['warmup_sessions'])
    if any(record.get(k) != v for k, v in expected.items() if k != 'declared_at'):
        raise ValueError('Evaluation window differs from its evidence-only selection rule')
    declared = pd.Timestamp(record['declared_at'])
    if declared.tzinfo is None or declared > pd.Timestamp.now(tz='UTC'):
        raise ValueError('Evaluation window declaration requires a past timezone-aware timestamp')
    return record


def main():
    from quant.pipeline.cli import parser_config
    from quant.storage.parquet_store import read_parquet_file
    parser, config = parser_config(__doc__)
    parser.add_argument('--search-audit', type=Path, required=True)
    parser.add_argument('--warmup-sessions', type=int, default=252)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    calendar = read_parquet_file(args.config(config).calendar_path)
    sessions = calendar.loc[calendar.is_trading_session & pd.to_datetime(calendar.trade_date).le(pd.Timestamp(args.end)), 'trade_date']
    events = json.loads(args.search_audit.read_text(encoding='utf-8'))
    record = select_evaluation_window(args.start, sessions, events, warmup_sessions=args.warmup_sessions)
    freeze_evaluation_window(record, args.output)
    print(json.dumps(record, indent=2))


if __name__ == '__main__':
    main()
