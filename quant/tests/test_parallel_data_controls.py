import pandas as pd

from quant.features.tests.test_fundamental_snapshot import filing


def test_missing_cells_have_all_eight_causal_failure_categories():
    from quant.research.coverage_deficits import coverage_deficits, FAILURE_REASONS
    names = list('abcdefgh')
    cross = pd.DataFrame(dict(instrument_id=names, symbol=[s.upper() for s in names], adv60=1e8))
    rows = [filing(filing_id=name, instrument_id=name, symbol=name.upper()) for name in names if name != 'b']
    rows[0].update(document_sha256=None, parser_status='NOT_ATTEMPTED')
    for row in rows:
        if row['instrument_id'] == 'e':
            row['revision_at'] = '2024-09-01T16:00:00+05:30'
        if row['instrument_id'] == 'f':
            row['instrument_id'] = None
        if row['instrument_id'] == 'h':
            row.update(period_start='2020-04-01', period_end='2021-03-31', period_type='Annual')
    attempts = {
        'c': dict(parser_status='NEEDS_REVIEW', review=[dict(reason='HTTP 403')]),
        'd': dict(parser_status='NEEDS_REVIEW', review=[dict(reason='Unsupported taxonomy')]),
        'g': dict(parser_status='NEEDS_REVIEW', review=[dict(reason='Unsupported ENTITY')]),
    }
    result = coverage_deficits(cross, pd.DataFrame(rows), set(), cross,
        pd.Timestamp('2024-08-02T16:00:00+05:30'), attempts=attempts)
    assert result['coverage_failure_attribution'] == dict.fromkeys(FAILURE_REASONS, 1)
    assert {row['instrument_id']: row['failure_reason'] for row in result['missing_details']}['e'] == 'timing_failure'


def test_complete_capital_event_requires_post_credit_availability_and_lineage(tmp_path):
    from quant.tests.test_historical_forward_validation import verified_event
    from quant.pipeline.verify_capital_events import verify_capital_events
    row = verified_event(tmp_path)
    row['known_at'] = row['event_evidence']['known_at']['value'] = '2024-04-02T16:00:00+05:30'
    result = verify_capital_events(pd.DataFrame([row]), tmp_path)
    assert result.verification_status.iloc[0] != 'VERIFIED_COMPLETE'
    assert 'valid_dates' in result.verification_missing_facts.iloc[0]
    row = verified_event(tmp_path)
    row['event_type'] = row['event_evidence']['event_type']['value'] = 'SPLIT'
    assert verify_capital_events(pd.DataFrame([row]), tmp_path).verification_status.iloc[0] != 'VERIFIED_COMPLETE'
    for key in ('predecessor_instrument_id', 'successor_instrument_id'):
        row[key] = 'a'
        row['event_evidence'][key] = dict(row['event_evidence']['instrument_id'], value='a')
    assert verify_capital_events(pd.DataFrame([row]), tmp_path).verification_status.iloc[0] == 'VERIFIED_COMPLETE'
