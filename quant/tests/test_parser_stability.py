import pandas as pd
import pytest
from quant.pipeline.report_fundamental_parser_stability import parser_stability


def test_attempt_denominators_and_failure_groups_are_explicit():
    filings=pd.DataFrame([dict(filing_id='a',first_seen_at='2026-11-18',instrument_id='liquid',
        timing_status='VERIFIED',financial_schema='BANK',period_type='Quarterly'),
        dict(filing_id='b',first_seen_at='2026-11-18',instrument_id=None,timing_status='UNCERTAIN',period_type='Annual')])
    attempts={'a':dict(parser_status='PARSED',document_sha256='a'*64,taxonomy='bank'),
        'b':dict(parser_status='NEEDS_REVIEW',taxonomy='unknown',review=[{'reason':'NO_DOCUMENT'}])}
    universe=pd.DataFrame([dict(as_of='2026-11-17',instrument_id='missing',eligible=True,adv60=1e9)])
    report=parser_stability(filings,attempts,universe=universe,as_of='2026-11-17')
    assert report['documents_attempted']==2 and report['documents_downloaded']==1
    assert report['parse_success_pct']==50 and report['timing_verified_pct']==50
    assert report['identity_resolved_pct']==50
    assert report['failure_by_reason']=={'NO_DOCUMENT':1}
    assert report['failure_by_taxonomy']=={'unknown':1}
    assert report['failure_by_period_type']=={'Annual':1}
    assert report['top100_adv_unresolved_filings'][0]['instrument_id']=='missing'
    assert not report['date_range_expansion_allowed']


def test_empty_attempts_are_unassessed_not_success():
    report=parser_stability(pd.DataFrame(),{})
    assert report['parse_success_pct'] is None
    assert report['parser_stability']=='UNESTABLISHED'
