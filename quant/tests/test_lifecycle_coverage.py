import pandas as pd

from quant.pipeline.audit_security_lifecycle_gaps import audit_security_lifecycle_gaps
from quant.pipeline.lifecycle_review_queue import lifecycle_review_queue


def test_final_quote_audit_ignores_future_evidence_and_optional_tender_economics():
    dates = pd.bdate_range('2024-01-01', periods=20)
    quotes = pd.DataFrame(dict(instrument_id=['a','b','c'], symbol=['A','B','C'], trade_date=[dates[1],dates[2],dates[-1]]))
    events = pd.DataFrame([dict(instrument_id='a', event_type='CASH_SETTLEMENT', effective_date=dates[3],
        announced_at='2024-03-01T16:00:00+05:30', verification_status='VERIFIED', lifecycle_event_id='future', mandatory=True, optional=False),
        dict(instrument_id='b', event_type='SUSPENDED', effective_date=dates[3], announced_at='2024-01-03T16:00:00+05:30',
             verification_status='VERIFIED', lifecycle_event_id='suspension', mandatory=False, optional=False),
        dict(instrument_id='b', event_type='EXIT_OFFER', effective_date=dates[4], announced_at='2024-01-04T16:00:00+05:30',
             verification_status='VERIFIED', lifecycle_event_id='optional', mandatory=False, optional=True)])
    gaps = audit_security_lifecycle_gaps(quotes,dates,events,dates[-1]).set_index('instrument_id')
    assert len(gaps) == 2
    assert gaps.loc['a','candidate_event'] == 'UNEXPLAINED_FINAL_QUOTE'
    assert gaps.loc['b','candidate_event'] == 'VERIFIED_SUSPENSION'
    assert not gaps.economic_resolution_verified.any()


def test_review_queue_prioritizes_real_holdings_and_never_uses_future_scores():
    gaps = pd.DataFrame(dict(instrument_id=list('abcd'), symbol=list('ABCD'),
        last_quoted_date=pd.to_datetime(['2024-01-01']*4), candidate_event=['UNEXPLAINED_FINAL_QUOTE']*4,
        economic_resolution_verified=[False]*4))
    holdings = pd.DataFrame(dict(instrument_id=['a'], trade_date=['2024-01-01'], value=[100]))
    scores = pd.DataFrame(dict(instrument_id=['b','d'], as_of=['2024-01-01','2025-01-01'],percentile_score=[95,99]))
    eligible = pd.DataFrame(dict(instrument_id=['c'], as_of=['2024-01-01'], eligible=[True]))
    queue = lifecycle_review_queue(gaps,holdings=holdings,scores=scores,eligible=eligible,as_of='2024-02-01')
    assert queue.review_priority.tolist() == [1,2,3,4]
    assert queue.iloc[0].review_status == 'BLOCKED_HELD_ECONOMICS'


def test_inventory_without_observed_quotes_remains_an_unresolved_review_candidate():
    inventory = pd.DataFrame(dict(symbol=['NEW'],source_url=['https://nsearchives.nseindia.com/list.csv']))
    queue = lifecycle_review_queue(pd.DataFrame(),inventories=inventory)
    assert len(queue) == 1 and pd.isna(queue.iloc[0].instrument_id)
    assert queue.iloc[0].review_status == 'NEEDS_IDENTITY_REVIEW'
    assert queue.iloc[0].review_priority == 4


def test_quote_scan_uses_historical_eq_identity_and_tracks_series_changes(tmp_path):
    from quant.config import Config
    from quant.storage.parquet_store import write_parquet
    from quant.pipeline.audit_security_lifecycle_gaps import load_last_quotes
    rows = pd.DataFrame([
        dict(isin='INE000000001',symbol='OLD',series='EQ',trade_date=pd.Timestamp('2024-01-01'),volume=10,close=100),
        dict(isin='INE000000001',symbol='NEW',series='BE',trade_date=pd.Timestamp('2024-01-02'),volume=10,close=100),
        dict(isin='INE000000002',symbol='BOND',series='N1',trade_date=pd.Timestamp('2024-01-01'),volume=10,close=100),
        dict(isin='INE000000003',symbol='FUTURE',series='BE',trade_date=pd.Timestamp('2024-01-01'),volume=10,close=100),
        dict(isin='INE000000003',symbol='FUTURE',series='EQ',trade_date=pd.Timestamp('2024-01-05'),volume=10,close=100)])
    write_parquet(rows,tmp_path/'normalized/prices/bars.parquet')
    quotes = load_last_quotes(Config(data_dir=tmp_path),pd.Timestamp('2024-01-03').date())
    assert quotes['isin'].tolist() == ['INE000000001']
    assert quotes.iloc[0].last_quoted_date == pd.Timestamp('2024-01-02')
