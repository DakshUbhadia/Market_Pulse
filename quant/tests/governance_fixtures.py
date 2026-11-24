"""Explicitly synthetic attestations and interval evidence for contract tests."""
from quant.forward.signal_store import content_hash
import pandas as pd


def human_review(review_type, subject, decision, **fields):
    from quant.governance.review import transition_subject_id, POSITIVE_DECISIONS
    body = dict(review_type=review_type, subject_sha256=subject, decision=decision,
        status='APPROVED' if decision in POSITIVE_DECISIONS else 'REJECTED',
        subject_id=transition_subject_id(fields.get('transition_id', 'SYNTHETIC_TEST_SUBJECT')),
        reviewer_kind='HUMAN', independent_review=True, reviewer_name='SYNTHETIC TEST PERSON',
        reviewer_role='SYNTHETIC TEST ONLY', reason='Synthetic governance contract test',
        reviewed_at=pd.Timestamp.now(tz='UTC').isoformat(), performance_information_used=False)
    body.update(fields)
    return dict(body, sha256=content_hash(body))


def freeze_test_specification(spec, output, *, coverage_reports):
    from quant.research.data_interval import certify_data_interval
    from quant.research.specification import freeze_specification, specification_subject
    interval = certify_data_interval(coverage_reports['filings'], coverage_reports['shares'], matrix=coverage_reports['matrix'])
    approve_test_gate(output.parent)
    review = human_review('V2_SPEC_APPROVAL', specification_subject(spec, coverage_reports, interval), 'APPROVE',
                         subject_id=spec['spec_version'])
    return freeze_specification(spec, output, coverage_reports=coverage_reports,
                               governance_review=review, data_interval=interval)


def approve_test_gate(data_dir, *, decision='CONFIRM_EVIDENCE_EXHAUSTED_UNRESOLVED'):
    """Synthetic human-shaped authority under a temporary test root, never real approval."""
    from pathlib import Path
    from quant.governance.gates import GateRegistry, default_gate, SUBJECT_ID
    from quant.governance.review import seal_review
    gate = default_gate()
    review = human_review('TRANSITION_EXHAUSTION', gate['subject_sha256'], decision,
        subject_id=SUBJECT_ID, transition_id='TIDEWATER-2016-03-17',
        automated_review_sha256=gate['subject_sha256'], sources_reviewed=['SYNTHETIC TEST ONLY'],
        facts_proven=['SYNTHETIC TEST FACT'], facts_unproven=['SYNTHETIC TEST MISSING FACT'],
        search_routes_attempted=['SYNTHETIC TEST ROUTE'], scope='SYNTHETIC_TEST_ONLY')
    path = Path(data_dir)/'synthetic-human-review.json'
    registry = GateRegistry(data_dir)
    if not path.exists():
        seal_review(review, path)
        registry.decide(path)
    else:
        import json
        review = json.loads(path.read_text(encoding='utf-8'))
    if decision == 'CONFIRM_EVIDENCE_EXHAUSTED_UNRESOLVED':
        from quant.config import REPO_ROOT
        from quant.research.evaluation_window import freeze_evaluation_window, window_subject, window_subject_id
        import json
        output = Path(data_dir)/'reports/v1-evaluation-window-admitted.json'
        if not output.exists():
            declaration = json.loads((REPO_ROOT/'quant/artifacts/historical-forward-validation/reports/v1-evaluation-declaration.json').read_text(encoding='utf-8'))
            declaration = {k: v for k, v in declaration.items() if k not in ('sha256', 'governance')}
            window_review = human_review('EVALUATION_WINDOW_ADMISSION', window_subject(declaration), 'ADMIT',
                subject_id=window_subject_id(declaration))
            freeze_evaluation_window(declaration, output, governance=dict(
                transition_reviews={'TIDEWATER-2016-03-17': review}, window_review=window_review))
    return registry


def complete_interval(anchors, events, coverage):
    from quant.data.capital_events import anchor_hash, event_inventory_hash
    result = coverage.copy()
    for i, row in result.iterrows():
        known = anchors[anchors.instrument_id.eq(row.instrument_id)].sort_values('effective_date')
        result.loc[i, 'interval_start'] = str(known.iloc[0].effective_date)
        result.loc[i, 'interval_end'] = str(row.covered_through)
        result.loc[i, 'unresolved_event_count'] = 0
        result.loc[i, 'event_inventory_hash'] = event_inventory_hash(events, row.instrument_id, known.iloc[0].effective_date, row.covered_through)
        result.loc[i, 'reconciled_start_anchor'] = anchor_hash(known.iloc[0])
        result.loc[i, 'reconciled_end_anchor'] = anchor_hash(known.iloc[-1])
    result['source_coverage'] = [{'synthetic-inventory.json': 'a'*64} for _ in range(len(result))]
    return result
