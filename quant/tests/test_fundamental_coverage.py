from datetime import date
import pandas as pd

from quant.pipeline.audit_fundamental_coverage import audit_fundamental_coverage, verify_filing_archives
from quant.features.tests.test_fundamental_snapshot import filing


def test_coverage_counts_universe_and_liquidity_with_pit_revisions():
    dates = pd.bdate_range('2024-07-01','2024-09-30')
    universe = pd.DataFrame([dict(as_of=day,instrument_id=name,eligible=True,adv60=100-i,entity_type=category)
        for day in [pd.Timestamp('2024-07-31'),pd.Timestamp('2024-08-30'),pd.Timestamp('2024-09-30')]
        for i,(name,category) in enumerate([('a','bank'),('b','industrial'),('c','nbfc')])])
    result = audit_fundamental_coverage(universe,pd.DataFrame([filing()]),dates,
        start=date(2024,7,1),end=date(2024,9,30),top_liquidity_count=1)
    july, august, september = result['periods']
    assert july['usable_fundamentals_count'] == 0
    assert august['eligible_universe_count'] == 3 and august['usable_fundamentals_count'] == 1
    assert august['top_liquidity_coverage_pct'] == 100
    assert august['bank_coverage'] == 100 and august['nbfc_coverage'] == 0
    assert result['first_reliable_fundamental_signal_date'] is None
    all_filings = pd.DataFrame([filing(filing_id=name,instrument_id=name) for name in 'abc'])
    result = audit_fundamental_coverage(universe,all_filings,dates,start=date(2024,7,1),end=date(2024,9,30))
    assert result['first_reliable_fundamental_signal_date'] is None  # two passing months cannot certify an interval


def test_missing_period_universe_and_missing_archive_cannot_certify_coverage(tmp_path):
    rows = pd.DataFrame([filing()])
    verified = verify_filing_archives(rows,tmp_path)
    assert verified.parser_status.eq('NEEDS_REVIEW').all()
    result = audit_fundamental_coverage(pd.DataFrame(),rows,pd.bdate_range('2024-08-01','2024-08-30'),
                                       start=date(2024,8,1),end=date(2024,8,30))
    assert not result['reliable_window_established']
    assert result['periods'][0]['coverage_pct'] is None


def test_compact_coverage_preserves_historical_eligibility_and_missing_quotes():
    from quant.tests.research_fixtures import market_fixture
    from quant.pipeline.audit_fundamental_coverage import historical_coverage_universe, coverage_dates
    from quant.universe.eligible import build_eligible_universe
    prices,_,sessions = market_fixture(stocks=2,days=300,start='2023-01-02')
    cutoffs = coverage_dates(sessions,sessions[0],sessions[-1],'monthly')
    prices = prices[~(prices.instrument_id.eq('id-001') & prices.trade_date.eq(cutoffs[-1]))]
    compact = historical_coverage_universe(prices,sessions,sessions[0],sessions[-1])
    full = build_eligible_universe(prices,sessions)
    expected = full[full.as_of.isin(cutoffs)]
    columns = ['as_of','instrument_id','eligible','adv60','history_sessions']
    pd.testing.assert_frame_equal(compact[columns].sort_values(columns[:2]).reset_index(drop=True),
                                  expected[columns].sort_values(columns[:2]).reset_index(drop=True))
