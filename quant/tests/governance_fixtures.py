"""Explicitly synthetic attestations and interval evidence for contract tests."""
from quant.forward.signal_store import content_hash
import pandas as pd


def human_review(review_type, subject, decision, **fields):
    body = dict(review_type=review_type, subject_sha256=subject, decision=decision,
        reviewer_kind='HUMAN', independent_review=True, reviewer_name='SYNTHETIC TEST PERSON',
        reviewer_role='SYNTHETIC TEST ONLY', reason='Synthetic governance contract test',
        reviewed_at=pd.Timestamp.now(tz='UTC').isoformat(), performance_information_used=False)
    body.update(fields)
    return dict(body, sha256=content_hash(body))


def freeze_test_specification(spec, output, *, coverage_reports):
    from quant.research.data_interval import certify_data_interval
    from quant.research.specification import freeze_specification, specification_subject
    interval = certify_data_interval(coverage_reports['filings'], coverage_reports['shares'])
    review = human_review('V2_SPEC_APPROVAL', specification_subject(spec, coverage_reports, interval), 'APPROVE')
    return freeze_specification(spec, output, coverage_reports=coverage_reports,
                               governance_review=review, data_interval=interval)


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
