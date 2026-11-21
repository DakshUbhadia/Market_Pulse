"""Validate and archive explicit human decisions, bound to the reviewed subject.

These are attributed attestations, not identity authentication. Automation may
prepare a packet but must never populate a human's identity or decision.
"""
import json
from pathlib import Path
import re

import pandas as pd

from quant.forward.signal_store import append_record, content_hash

DECISIONS = {
    'TRANSITION_EXHAUSTION': {'CONFIRM_EVIDENCE_EXHAUSTED_UNRESOLVED', 'REOPEN_SEARCH'},
    'EVALUATION_WINDOW_ADMISSION': {'ADMIT', 'REJECT'},
    'V2_SPEC_APPROVAL': {'APPROVE', 'REJECT'},
    'MODEL_PROMOTION': {'PROMOTE', 'REJECT'},
    'PRODUCTION_PUBLISHING': {'APPROVE', 'REJECT'},
}


def validate_review(record, *, review_type, subject_sha256, decision=None):
    if review_type not in DECISIONS:
        raise ValueError('Unknown governance review type')
    if (record.get('review_type') != review_type
            or record.get('subject_sha256') != subject_sha256
            or not re.fullmatch('[0-9a-f]{64}', str(subject_sha256))):
        raise ValueError('Human governance review does not bind this subject')
    if (record.get('reviewer_kind') != 'HUMAN' or record.get('independent_review') is not True
            or record.get('status', 'REVIEWED') != 'REVIEWED'
            or any(not isinstance(record.get(k), str) or not record[k].strip()
                   for k in ('reviewer_name', 'reviewer_role', 'reason', 'reviewed_at'))):
        raise ValueError('An attributed independent human governance review is required')
    reviewed = pd.Timestamp(record['reviewed_at'])
    if reviewed.tzinfo is None or pd.isna(reviewed) or reviewed > pd.Timestamp.now(tz='UTC'):
        raise ValueError('Human review requires a past timezone-aware timestamp')
    if record.get('decision') not in DECISIONS[review_type] or (decision and record['decision'] != decision):
        raise ValueError('Human governance decision does not authorize this action')
    if type(record.get('performance_information_used')) is not bool:
        raise ValueError('Record whether performance information influenced the decision')
    if review_type in ('TRANSITION_EXHAUSTION', 'EVALUATION_WINDOW_ADMISSION', 'V2_SPEC_APPROVAL'):
        if record['performance_information_used'] is not False:
            raise ValueError('This human review must be independent of performance')
    if review_type == 'TRANSITION_EXHAUSTION':
        if (not record.get('transition_id') or record.get('automated_review_sha256') != subject_sha256
                or any(not isinstance(record.get(k), list) or not record[k]
                       or any(not isinstance(v, str) or not v.strip() for v in record[k])
                       for k in ('sources_reviewed', 'facts_proven', 'facts_unproven', 'search_routes_attempted'))):
            raise ValueError('Transition review requires the complete human evidence assessment')
    return record


def seal_review(record, output):
    body = {k: v for k, v in record.items() if k != 'sha256'}
    validate_review(body, review_type=body.get('review_type'), subject_sha256=body.get('subject_sha256'))
    sealed = dict(body, sha256=content_hash(body))
    append_record(Path(output), sealed)
    return sealed


def require_review(record, *, review_type, subject_sha256, decision):
    if not isinstance(record, dict):
        raise ValueError('An immutable human governance review is required')
    body = {k: v for k, v in record.items() if k != 'sha256'}
    if record.get('sha256') != content_hash(body):
        raise ValueError('Human governance review checksum changed or is missing')
    return validate_review(record, review_type=review_type, subject_sha256=subject_sha256, decision=decision)


def main():
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--review', type=Path, required=True, help='Completed human attestation JSON')
    parser.add_argument('--output', type=Path, required=True, help='New immutable record path')
    args = parser.parse_args()
    seal_review(json.loads(args.review.read_text(encoding='utf-8')), args.output)
    print(args.output)


if __name__ == '__main__':
    main()
