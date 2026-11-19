from pathlib import Path
import json

import numpy as np
import pandas as pd
import pytest

from quant.data.xbrl import extract_financials
from quant.features.fundamentals import fundamental_observations
from quant.features.growth import growth_features
from quant.features.quality import quality_features
from quant.features.value import value_features
from quant.features.bank_fundamentals import bank_features
from quant.features.tests.test_fundamental_snapshot import filing
from quant.models.factor_v2 import same_universe_scores
from quant.portfolio.constraints import RiskPolicy
from quant.portfolio.covariance import shrinkage_covariance
from quant.portfolio.risk_budget import allocate_risk
from quant.research.purged_cv import purged_walk_forward, date_balanced_weights
from quant.storage.research_store import digest_file
from quant.tests.test_point_in_time import instance


def test_real_exchange_fixtures_select_quarter_instead_of_mislabeled_ytd():
    root = Path(__file__).parent/'fixtures/financials'
    for item in json.loads((root/'manifest.json').read_text())['fixtures']:
        path = root/item['file']
        assert digest_file(path) == item['sha256']
        result = extract_financials(path.read_bytes(),item['period_end'],period_start=item['period_start'],
            consolidated=item['basis']=='Consolidated',entity_type=item['entity_type'])
        assert result['parser_status'] == 'PARSED'
        assert {k:result[k] for k in item['expected']} == item['expected']


def test_namespace_currency_and_context_ambiguity_fail_closed():
    good = '<f:RevenueFromOperations contextRef="q" unitRef="INR">123</f:RevenueFromOperations>'
    for content in [instance(good).replace(b'urn:finance',b'urn:foreign'),
                    instance(good).replace(b'f:INR</measure>',b'f:USD</measure>'),
                    instance(good+good.replace('123','456'))]:
        assert extract_financials(content,'2024-06-30')['revenue'] is None


def test_text_basis_cannot_override_a_conflicting_consolidation_member():
    content = instance('<f:NatureOfReportStandaloneConsolidated contextRef="q">Standalone</f:NatureOfReportStandaloneConsolidated>'
        '<f:RevenueFromOperations contextRef="q" unitRef="INR">123</f:RevenueFromOperations>')
    assert extract_financials(content,'2024-06-30',consolidated=True)['revenue'] is None


def test_growth_value_and_bank_rules_do_not_invent_inputs():
    assert np.isnan(growth_features(dict(quarter_fresh=True,quarter_pat=10,prior_quarter_pat=-10))['pat_yoy'])
    row=dict(annual_fresh=True,annual_pat=100.,annual_equity=500.,annual_operating_cash_flow=120.,annual_capex=20.)
    assert all(np.isnan(v) for v in value_features(row,raw_price=10,shares=dict(value_feature_valid=False)).values())
    values=value_features(row,raw_price=10,shares=dict(value_feature_valid=True,shares_outstanding=100))
    assert values == dict(earnings_yield=.1,book_yield=.5,fcf_yield=.1)
    assert all(np.isnan(v) for v in quality_features(dict(row,entity_type='IND_AS_BANK')).values())
    assert np.isnan(bank_features(dict(row,entity_type='IND_AS_BANK'))['bank_roa'])


def test_fundamental_observations_are_causal_and_preserve_missing_history():
    rows = pd.DataFrame([filing(entity_type='IND_AS_INDUSTRIAL'),filing(filing_id='future',
        entity_type='IND_AS_INDUSTRIAL',revenue=999.,revision_at='2024-09-01T16:00:00+05:30')])
    result=fundamental_observations(rows,'2024-08-02T16:00:00+05:30').iloc[0]
    assert result.quarter_revenue==100
    assert np.isnan(result.prior_quarter_revenue)
    assert not result.annual_fresh


def test_covariance_excludes_future_and_never_fills_missing_observations():
    rng=np.random.default_rng(7)
    returns=pd.DataFrame(rng.normal(0,.01,(260,3)),index=pd.bdate_range('2024-01-01',periods=260),columns=list('abc'))
    cutoff=returns.index[230]
    first,meta=shrinkage_covariance(returns,cutoff)
    returns.loc[returns.index>cutoff]=999
    second,_=shrinkage_covariance(returns,cutoff)
    pd.testing.assert_frame_equal(first,second)
    assert meta['observations']==231
    returns.loc[returns.index[:20],'a']=np.nan
    with pytest.raises(ValueError,match='jointly observed'):
        shrinkage_covariance(returns,cutoff)


def test_risk_budget_enforces_caps_clusters_volatility_and_order_capacity():
    names=pd.Index(['a','b','c','d'])
    sigma=pd.DataFrame(np.eye(4)*.09,index=names,columns=names)
    old=pd.Series(0.,index=names)
    adv=pd.Series(1_000_000.,index=names)
    groups=pd.Series(['x','x','y','y'],index=names)
    policy=RiskPolicy(max_weight=.5,max_cluster_weight=.4,target_volatility=.12)
    weights,report=allocate_risk(sigma,old,adv,groups,nav=100_000,policy=policy)
    assert (weights<=.1+1e-8).all()  # INR 10k daily capacity / INR 100k NAV.
    assert weights.groupby(groups).sum().max() <= .4+1e-8
    assert report['annualized_volatility'] <= .12+1e-7
    assert report['cash_weight'] >= .6-1e-7
    with pytest.raises(ValueError,match='positive portfolio capital'):
        allocate_risk(sigma,old,adv,groups,nav=0,policy=policy)


def test_risk_budget_rejects_infeasible_capacity_limited_exit():
    sigma=pd.DataFrame([[.1]],index=['a'],columns=['a'])
    with pytest.raises(ValueError,match='Infeasible'):
        allocate_risk(sigma,pd.Series({'a':.5}),pd.Series({'a':1}),pd.Series({'a':'x'}),nav=100_000,selected=set())


def test_purged_folds_and_date_weights_do_not_leak_overlapping_labels():
    dates=pd.bdate_range('2020-01-01',periods=100)
    samples=pd.DataFrame(dict(as_of=dates[:90],exit_date=dates[10:]))
    folds=list(purged_walk_forward(samples,dates,min_train_sessions=20,test_sessions=10,embargo_sessions=5))
    assert folds
    for train,test in folds:
        assert samples.iloc[train].exit_date.max() < samples.iloc[test].as_of.min()
        assert dates.get_loc(samples.iloc[test].as_of.min())-dates.get_loc(samples.iloc[train].exit_date.max()) >= 6
    weights=date_balanced_weights([dates[0],dates[0],dates[1]])
    assert weights.tolist()==[.5,.5,1.]


def test_v2_and_matched_v1_use_identical_covered_names():
    from quant.features.matrix import SCORE_FEATURES
    from quant.version import FEATURE_VERSION
    frame=pd.DataFrame(dict(as_of=pd.Timestamp('2024-08-01'),instrument_id=list('abcd'),
        eligible=True,feature_valid=True,feature_version=FEATURE_VERSION))
    for i,name in enumerate(SCORE_FEATURES):
        frame[name]=np.arange(4)+i+1.
        frame['z_'+name]=np.arange(4)-1.5
    fields=['roe','cfo_pat','debt_equity','revenue_yoy','pat_yoy','earnings_yield','fcf_yield','book_yield']
    fundamentals=frame[['as_of','instrument_id']].copy().assign(entity_type='IND_AS_INDUSTRIAL', value_feature_valid=True)
    for name in fields:
        fundamentals[name]=[1.,2.,3.,np.nan]
    result=same_universe_scores(frame,fundamentals,min_group_size=2)
    assert set(result['full_v1'].instrument_id)==set('abcd')
    assert set(result['matched_v1'].instrument_id)==set(result['factor_v2'].instrument_id)==set('abc')
    assert not result['factor_v2'].raw_score.isna().any()
    assert result['factor_v2'].model_version.eq('factor_v2_candidate_1.0.0').all()


def test_numpy_ledoit_wolf_matches_published_numerical_example():
    rng=np.random.RandomState(0)
    data=rng.multivariate_normal([0,0],[[.4,.2],[.2,.8]],size=50)
    returns=pd.DataFrame(data,index=pd.bdate_range('2020-01-01',periods=50))
    matrix,report=shrinkage_covariance(returns,returns.index[-1],lookback=50,min_observations=50)
    np.testing.assert_allclose(matrix.to_numpy()/252,[[.44,.16],[.16,.80]],atol=.01)
    assert report['shrinkage']==pytest.approx(.23,abs=.01)


def reviewed_spec():
    from quant.config import REPO_ROOT
    spec = json.loads((REPO_ROOT/'quant/specs/factor_v2_1.0.0.json').read_text())
    spec.update(review_status='REVIEWED', reviewed_by='synthetic-test-review',
        evaluation_windows=[{'from':'2024-01-01','to':'2026-01-01'}])
    return spec


def synthetic_coverage_reports(spec):
    dates = pd.date_range(pd.Timestamp(spec['evaluation_windows'][0]['from'])-pd.DateOffset(months=13),
                          pd.Timestamp(spec['evaluation_windows'][-1]['to'])+pd.offsets.MonthEnd(0), freq='ME')
    periods = [dict(as_of=str(d.date()), coverage_pct=100., top_liquidity_coverage_pct=100.,
                    verified_share_coverage=100., top100_verified_share_coverage=100., thresholds_met=True) for d in dates]
    return {k:dict(scope='SYNTHETIC_TEST_ONLY', frequency='monthly', periods=periods) for k in ('filings', 'shares')}


def test_specification_rejects_draft_and_detects_tampering(tmp_path):
    from quant.research.specification import freeze_specification,load_specification
    spec=reviewed_spec()
    with pytest.raises(ValueError,match='review'):
        freeze_specification(dict(spec,review_status='DRAFT'),tmp_path/'draft.json')
    path=tmp_path/'frozen.json'
    freeze_specification(spec,path,coverage_reports=synthetic_coverage_reports(spec))
    assert load_specification(path)==spec
    record=json.loads(path.read_text())
    record['specification']['min_group_size']=2
    path.write_text(json.dumps(record))
    with pytest.raises(ValueError,match='checksum'):
        load_specification(path)


def test_v2_research_block_retains_outcome_without_completion(tmp_path, monkeypatch):
    from quant.config import Config
    from quant.research.specification import freeze_specification
    from quant.pipeline.run_factor_v2_research import run_factor_v2_research
    monkeypatch.setattr('quant.pipeline.run_factor_v2_research.require_certified_implementation', lambda *a: {'scope': 'SYNTHETIC_ONLY'})
    spec=tmp_path/'spec.json'
    freeze_specification(reviewed_spec(),spec,coverage_reports=synthetic_coverage_reports(reviewed_spec()))
    with pytest.raises(FileNotFoundError):
        run_factor_v2_research(Config(data_dir=tmp_path),spec_path=spec,
            price_baseline=tmp_path/'no-price-baseline',total_return_baseline=tmp_path/'no-tr-baseline',
            filings_path=tmp_path/'missing',anchors_path=tmp_path/'missing',events_path=tmp_path/'missing',
            share_coverage_path=tmp_path/'missing',output_root=tmp_path/'research')
    assert not list((tmp_path/'research').rglob('completion.json'))
    report=json.loads(next((tmp_path/'research').rglob('outcome.json')).read_text())
    assert report['status']=='BLOCKED' and not report['factor_v2_enabled']


def test_comparison_runs_shared_accounting_and_rejects_universe_mismatch():
    from quant.tests.research_fixtures import market_fixture
    from quant.research.multifactor import compare_models,v2_decision
    from quant.backtest.portfolio import PortfolioConfig
    from quant.backtest.costs import CostModel
    from quant.models.factor_v2 import BLOCKS
    prices,benchmark,sessions=market_fixture(stocks=12,days=350,start='2023-10-02')
    scores=prices[['trade_date','instrument_id']].rename(columns={'trade_date':'as_of'}).copy()
    scores['raw_score']=scores.instrument_id.str[-3:].astype(int).astype(float)
    scores['percentile_score']=scores.groupby('as_of').raw_score.rank(pct=True)*100
    scores['vol_63']=.2
    for block in BLOCKS:
        scores[block+'_score']=scores.raw_score
    labels=scores[['as_of','instrument_id']].assign(label_available=True,exit_date=scores.as_of,
        excess_return_63=scores.raw_score/100,stock_return_63=scores.raw_score/100)
    arms={name:scores.copy() for name in ('full_v1','matched_v1','factor_v2')}
    window={'from':str(sessions[270].date()),'to':str(sessions[-1].date())}
    risk_features = prices[['trade_date', 'instrument_id']].rename(columns={'trade_date':'as_of'}).assign(adv60=100_000_000.)
    result,ic=compare_models(prices,arms,labels,benchmark,sessions,window,
        portfolio=PortfolioConfig(holdings=2,max_weight=.5),cost_model=CostModel(allow_estimated_history=True), risk_features=risk_features)
    assert len(result) == 4
    assert all(r['metrics']['observations']==80 for r in result.values())
    assert all(set(r['stress'])=={'1.5','2.0'} for r in result.values())
    assert not ic.empty and set(ic.block)==set(BLOCKS)
    assert v2_decision([result],reviewed_spec()['acceptance'])['decision']=='INCONCLUSIVE'
    arms['matched_v1']=scores.iloc[1:]
    with pytest.raises(ValueError,match='identical dated'):
        compare_models(prices,arms,labels,benchmark,sessions,window)


def test_engine_risk_context_exposes_prior_close_marks_only():
    from quant.tests.research_fixtures import market_fixture,execution_scores
    from quant.backtest.engine import run_backtest
    from quant.backtest.portfolio import PortfolioConfig
    from quant.backtest.costs import CostModel
    prices,_,sessions=market_fixture(stocks=1,days=65,start='2024-10-01')
    calls=[]
    def target(scores,positions,config,**context):
        calls.append(context)
        return pd.Series({'id-000':.5})
    run_backtest(prices,execution_scores(prices),sessions,portfolio=PortfolioConfig(max_weight=.5),
        cost_model=CostModel(allow_estimated_history=True),target_builder=target,target_builder_context=True)
    first=calls[0]
    signal=first['signal_date']
    expected=prices.loc[prices.trade_date.eq(signal),'adjusted_close'].iloc[0]
    assert first['previous_bars']['id-000']['adjusted_close']==expected
    assert first['nav']==1_000_000
    assert set(first)=={'signal_date','nav','previous_bars'}


def test_nested_purging_keeps_inner_rows_inside_outer_training():
    from quant.research.purged_cv import nested_purged_walk_forward
    dates=pd.bdate_range('2020-01-01',periods=200)
    samples=pd.DataFrame(dict(as_of=dates[:-10],exit_date=dates[10:]))
    folds=list(nested_purged_walk_forward(samples,dates,outer_train_sessions=60,outer_test_sessions=20,
        inner_train_sessions=20,inner_test_sessions=10,embargo_sessions=5))
    assert folds
    for train,test,inner in folds:
        for a,b in inner:
            assert set(a)|set(b) <= set(train)
            assert not (set(b)&set(test))


def test_metadata_null_columns_accept_document_hashes_on_resume(tmp_path):
    from quant.pipeline.update_corporate import archive_filings
    from quant.data.nse_client import RawResponse
    from quant.data.http import sha256
    raw=instance('<f:RevenueFromOperations contextRef="q" unitRef="INR">123</f:RevenueFromOperations>')
    class Client:
        last_response=RawResponse('https://nsearchives.nseindia.com/doc.xml','2024-08-01T16:00:00+05:30',sha256(raw),tmp_path/'raw.xml',200)
        def get_bytes(self,*a,**k):
            return raw
    frame=pd.DataFrame([filing(document_sha256=np.nan,document_raw_path=np.nan,
        source_document='https://nsearchives.nseindia.com/doc.xml',bank=False,
        standalone_or_consolidated='Standalone')])
    result,review=archive_filings(Client(),frame,'financials',pd.DataFrame())
    assert result.document_sha256.iloc[0]==sha256(raw)
    assert result.revenue.iloc[0]==123 and not review


def test_stage1_supervisor_stops_on_source_failure(tmp_path,monkeypatch):
    from quant.pipeline import acquire_fundamentals_stage1 as stage
    from quant.config import Config
    from datetime import date
    calls=[]
    def batch(*args,**kwargs):
        calls.append(kwargs['limit'])
        return dict(status='BLOCKED_SOURCE',attempted_this_batch=1,parsed=0,needs_review=1,remaining_unattempted=99)
    monkeypatch.setattr(stage,'backfill_documents',batch)
    from quant.storage.parquet_store import write_parquet
    write_parquet(pd.DataFrame([filing(document_sha256=None, source_document='https://nsearchives.nseindia.com/doc.xml')]),
                  tmp_path/'normalized/financials/metadata.parquet')
    report=stage.acquire_stage1(Config(data_dir=tmp_path),date(2024,1,1),date(2024,12,31),max_batches=1,plan_path=tmp_path/'plan.json')
    assert calls==[100] and report['status']=='LIVE_SOURCE_UNAVAILABLE'


def test_document_batch_stops_after_first_source_failure(tmp_path,monkeypatch):
    from contextlib import nullcontext
    from datetime import date
    from unittest.mock import Mock
    from quant.config import Config
    from quant.storage.parquet_store import write_parquet
    from quant.pipeline import backfill_fundamental_documents as batch
    rows=pd.DataFrame([filing(filing_id=str(i),source_document='https://nsearchives.nseindia.com/doc.xml',
        first_seen_at='2024-08-02T16:00:00+05:30',source_url='https://www.nseindia.com/api/test',
        source_sha256='a'*64,metadata_raw_path='raw.json',document_sha256=None) for i in range(3)])
    write_parquet(rows,tmp_path/'normalized/financials/metadata.parquet')
    write_parquet(pd.DataFrame(),tmp_path/'normalized/security_history/identities.parquet')
    monkeypatch.setattr(batch,'NseClient',lambda _:nullcontext(object()))
    monkeypatch.setattr(batch,'FinancialVersionStore',lambda _:Mock())
    def fail(client,frame,*args):
        frame['parser_status']='NEEDS_REVIEW'
        return frame,[dict(source_status='LIVE_SOURCE_UNAVAILABLE',reason='HTTP 403')]
    monkeypatch.setattr(batch,'archive_filings',fail)
    monkeypatch.setattr('quant.pipeline.report_fundamental_parser_stability.report_parser_stability',lambda *a:None)
    result=batch.backfill_documents(Config(data_dir=tmp_path),date(2024,1,1),date(2024,12,31),limit=100)
    assert result['status']=='BLOCKED_SOURCE'
    assert result['attempted_this_batch']==1 and result['remaining_unattempted']==2


def test_bank_metadata_code_b_is_recognized_and_parser_version_survives_storage(tmp_path):
    from quant.data.nse_financials import parse_financial_filings
    from quant.data.nse_client import RawResponse
    from quant.data.normalization import write_observation
    from quant.storage.parquet_store import read_parquet_file
    raw=RawResponse('https://www.nseindia.com/api/test','2024-08-01T16:00:00+05:30','a'*64,tmp_path/'raw.json',200)
    rows=parse_financial_filings([dict(symbol='BANK',toDate='30-Jun-2024',bank='B',
        consolidated='Consolidated',exchdisstime='01-Aug-2024 16:00:00')],raw)
    assert bool(rows.bank.iloc[0])
    rows['parser_version']='financial_xbrl_2.0.0'
    path=write_observation(rows,tmp_path/'observations','a'*64,raw.fetched_at)
    assert read_parquet_file(path).parser_version.eq('financial_xbrl_2.0.0').all()


def test_complete_v2_runner_seals_synthetic_comparison_without_promotion(tmp_path,monkeypatch):
    from quant.config import Config
    from quant.tests.research_fixtures import market_fixture
    from quant.research.specification import freeze_specification
    from quant.pipeline import run_factor_v2_research as runner
    from quant.storage.parquet_store import write_parquet
    from quant.backtest.artifacts import verify_backtest_seal
    config=Config(data_dir=tmp_path)
    dates=pd.bdate_range('2023-01-02','2025-02-07')
    prices,benchmark,sessions=market_fixture(stocks=25,days=len(dates))
    raw=tmp_path/'raw/source.xml'
    raw.parent.mkdir()
    raw.write_bytes(b'synthetic archived source')
    digest=digest_file(raw)
    rows=[]
    for identity in sorted(prices.instrument_id.unique()):
        for i,(start,end,published,period) in enumerate([
            ('2022-04-01','2023-03-31','2023-05-01','Annual'),
            ('2023-04-01','2024-03-31','2024-05-01','Annual'),
            ('2023-10-01','2023-12-31','2024-01-10','Quarterly'),
            ('2024-10-01','2024-12-31','2025-01-10','Quarterly'),
            ('2023-07-01','2023-09-30','2023-11-10','Quarterly'),
            ('2024-07-01','2024-09-30','2024-11-10','Quarterly')]):
            rows.append(filing(filing_id=f'{identity}-{i}',instrument_id=identity,period_start=start,period_end=end,
                period_type=period,exchange_disseminated_at=published+'T16:00:00+05:30',
                source_sha256=digest,document_sha256=digest,metadata_raw_path=str(raw),document_raw_path=str(raw),
                entity_type='IND_AS_INDUSTRIAL',revenue=100.+i,pat=10.+i,equity=100.,assets=200.,borrowings=10.,
                operating_cash_flow=20.,capex=5.))
    identities=sorted(prices.instrument_id.unique())
    anchors=pd.DataFrame([dict(instrument_id=n,effective_date='2023-12-31',shares_outstanding=10.,
        exchange_disseminated_at='2023-12-31T16:00:00+05:30',verification_status='VERIFIED',source_sha256=digest,raw_path=str(raw)) for n in identities])
    anchors=pd.concat([anchors, anchors.assign(effective_date='2023-09-30',
        exchange_disseminated_at='2023-10-01T16:00:00+05:30')], ignore_index=True)
    coverage=pd.DataFrame([dict(instrument_id=n,covered_from='2023-09-30',covered_through='2025-02-07',
        known_at='2023-12-31T16:00:00+05:30',verification_status='VERIFIED',source_sha256=digest,raw_path=str(raw)) for n in identities])
    inputs=[tmp_path/n for n in ('filings.parquet','anchors.parquet','events.parquet','coverage.parquet')]
    for path,frame in zip(inputs,[pd.DataFrame(rows),anchors,pd.DataFrame(),coverage]):
        write_parquet(frame,path)
    spec=reviewed_spec()
    spec['evaluation_windows']=[dict(**{'from':'2025-01-01','to':'2025-02-07'})]
    spec_path=tmp_path/'frozen-spec.json'
    freeze_specification(spec,spec_path,coverage_reports=synthetic_coverage_reports(spec))
    # Only the external V1/data foundation is isolated. Feature construction,
    # PIT selection, coverage, all accounting comparisons and seals remain real.
    monkeypatch.setattr(runner,'require_completed_baselines',lambda *a:{'scope':'SYNTHETIC_TEST_ONLY'})
    monkeypatch.setattr(runner,'require_certified_implementation',lambda *a:{'scope':'SYNTHETIC_TEST_ONLY'})
    monkeypatch.setattr(runner,'require_research_ready',lambda *a:{'status':'SYNTHETIC_TEST_ONLY'})
    monkeypatch.setattr(runner,'input_manifest',lambda *a:{'scope':'SYNTHETIC_TEST_ONLY'})
    monkeypatch.setattr(runner,'verify_manifest',lambda *a:None)
    monkeypatch.setattr(runner,'load_research_data',lambda *a:(prices,benchmark,sessions,None,None))
    folder,decision=runner.run_factor_v2_research(config,spec_path=spec_path,price_baseline=tmp_path/'price',
        total_return_baseline=tmp_path/'total',filings_path=inputs[0],anchors_path=inputs[1],events_path=inputs[2],
        share_coverage_path=inputs[3],output_root=tmp_path/'research')
    assert verify_backtest_seal(folder)['status']=='COMPLETE'
    assert decision['decision']=='INCONCLUSIVE' and not decision['automatic_model_activation']
    assert len(list((folder/'window-00').glob('*/metrics.json')))==4
    assert (folder/'window-00/capacity-scenarios.json').is_file()
