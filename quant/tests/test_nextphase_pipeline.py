from datetime import date
from unittest.mock import Mock

import pandas as pd
import pytest

from quant.config import Config
from quant.pipeline import update_all as pipeline
from quant.pipeline.state import PipelineState
from quant.pipeline.scheduled_update import calculate_update_window
from quant.pipeline.update_calendar import refresh_calendar
from quant.pipeline.check_research_ready import check_research_ready
from quant.pipeline.audit_fundamentals import audit_fundamentals
from quant.features.adjustments import adjust_prices
from quant.data.http import Downloader
from test_calendar import calendar, fake_client


@pytest.mark.parametrize('failed_source',[False,True])
def test_clean_pipeline_builds_adjustments_before_enabled_filing_stage(tmp_path, monkeypatch, failed_source):
    config = Config(data_dir=tmp_path, enable_fundamentals=True)
    calls = []
    def refresh(*args, **kwargs):
        calls.append('calendar'); return pd.DataFrame(), {'status':'READY'}
    def market(*args):
        calls.append('market')
        return {source:{'status':'FAILED' if failed_source and source=='nse_bhavcopy' else 'READY'}
                for source in ('nse_bhavcopy','nse_security_master','nse_indices','nse_vix','security_history')}
    def stage(name):
        def run(cfg, start, end):
            calls.append(name)
            if name == 'adjusted':
                PipelineState(cfg).record('adjusted_prices', status='READY', **{'from':str(start),'to':str(end)})
            if name == 'filings':
                assert PipelineState(cfg).data['adjusted_prices']['status'] == 'READY'
            return {'status':'READY'}
        return run
    monkeypatch.setattr(pipeline,'refresh_calendar',refresh)
    monkeypatch.setattr(pipeline,'update_market_eod',market)
    for attribute,name in [('update_corporate_actions','actions'),('build_adjusted','adjusted'),
                           ('update_corporate_filings','filings'),('update_macro','macro')]:
        monkeypatch.setattr(pipeline,attribute,stage(name))
    def validate(*args, **kwargs):
        calls.append('validate')
        assert ('market_eod' in kwargs['run_errors']) == failed_source
        return {'status':'NOT_READY' if failed_source else 'READY'}
    monkeypatch.setattr(pipeline,'validate_data',validate)
    result=pipeline.update_all(config,date(2024,7,8),date(2024,7,9))
    assert calls == ['calendar','market','actions','adjusted','filings','macro','validate']
    assert result['status']==('NOT_READY' if failed_source else 'READY')


def test_scheduled_overlap_preserves_all_missed_sessions():
    dates = pd.bdate_range('2024-01-01',periods=25)
    frame = pd.DataFrame(dict(trade_date=dates,is_trading_session=True))
    state = {'market_eod':{'last_successful_session':str(dates[10].date())}}
    start,end = calculate_update_window(frame,state,target=dates[-1].date())
    assert start == dates[5].date() and end == dates[-1].date()
    assert calculate_update_window(frame,{})[0] == date(2018,1,1)


def test_incremental_calendar_does_not_rescan_prior_price_history(tmp_path,monkeypatch):
    from quant.storage.parquet_store import write_parquet
    cfg = Config(data_dir=tmp_path)
    write_parquet(calendar(),cfg.calendar_path)
    inspected = []
    def evidence(config,start,end):
        inspected.append((start,end)); return {},[]
    monkeypatch.setattr('quant.pipeline.update_calendar.loaded_bhavcopy_evidence',evidence)
    frame,_ = refresh_calendar(cfg,date(2024,7,5),date(2024,7,8),client=fake_client(),incremental=True)
    assert all(start==date(2024,7,5) and end==date(2024,7,8) for start,end in inspected)
    assert frame.trade_date.min().date() == date(2024,1,1)


def test_adjusted_ohlc_sequential_actions_and_dividend_separation():
    dates = pd.bdate_range('2024-01-01',periods=4)
    prices = pd.DataFrame(dict(trade_date=dates,instrument_id='a',symbol='A',series='EQ',
        open=[200,100,50,51],high=[210,105,52,53],low=[190,95,48,49],close=[200,100,50,51],source_hash='a'*64))
    actions = pd.DataFrame([dict(event_id='split',instrument_id='a',symbol='A',ex_date=dates[1],action_type='SPLIT',
        parse_status='PARSED',ratio_numerator=2,ratio_denominator=1,cash_amount=None),
        dict(event_id='bonus',instrument_id='a',symbol='A',ex_date=dates[2],action_type='BONUS',
        parse_status='PARSED',ratio_numerator=1,ratio_denominator=1,cash_amount=None)])
    result = adjust_prices(prices,actions)
    assert result.split_factor.tolist() == [.25,.5,1,1]
    assert result.adjusted_open.tolist() == [50,50,50,51]
    assert (result.adjusted_high >= result[['adjusted_open','adjusted_close']].max(axis=1)).all()
    assert result.source_price_sha256.eq('a'*64).all() and result.corporate_action_version.nunique()==1
    dividend = actions.iloc[:1].copy(); dividend['action_type']='DIVIDEND'; dividend['cash_amount']=2
    result = adjust_prices(prices,dividend)
    assert result.adjusted_open.tolist() == prices.open.tolist()


def test_research_gate_cannot_be_bypassed_by_missing_data(tmp_path):
    result = check_research_ready(Config(data_dir=tmp_path),as_of=date(2024,1,1))
    assert result['status']=='NOT_READY' and not result['price_history_ready']
    assert not result['recommendations_allowed']


def test_fundamental_audit_counts_versions_and_entity_types(tmp_path):
    from quant.storage.parquet_store import write_parquet
    document = tmp_path/'filing.xml'; document.write_bytes(b'<xbrl/>')
    frame = pd.DataFrame(dict(filing_id=['v1','v2'],first_seen_at=pd.to_datetime(['2024-08-01','2024-08-02']),
        period_end=pd.to_datetime(['2024-06-30']*2),entity_type=['bank','nbfc'],bank=[True,False],
        parser_status=['PARSED','NEEDS_REVIEW'],timing_status=['VERIFIED','UNCERTAIN'],
        instrument_id=['a',None],document_raw_path=[str(document)]*2))
    write_parquet(frame,tmp_path/'normalized/financials/versions.parquet')
    result = audit_fundamentals(Config(data_dir=tmp_path))
    assert result['total_filings_discovered']==2
    rows={row['entity_type']:row for row in result['by_year_and_entity_type']}
    assert rows['bank']['usable']==1 and rows['nbfc']['needs_review']==1


def test_overlap_refresh_retains_previous_raw_version(tmp_path):
    session = Mock(); session.get.side_effect=[Mock(content=b'first',status_code=200),Mock(content=b'revised',status_code=200)]
    downloader = Downloader(Config(request_interval=0),session)
    path=tmp_path/'report.csv'
    downloader.fetch('https://example.test/report',path)
    downloader.fetch('https://example.test/report',path,force=True)
    assert path.read_bytes()==b'revised'
    assert any(item.read_bytes()==b'first' for item in (tmp_path/'revisions').iterdir() if not item.name.endswith('.json'))


def test_historical_gate_uses_build_anchor_and_checks_unresolved_exclusions(tmp_path,monkeypatch):
    from quant.data.normalization import write_daily
    from quant.storage.parquet_store import write_parquet
    from quant.features.adjustments import action_version
    from quant.tests.research_fixtures import market_fixture
    config=Config(data_dir=tmp_path)
    prices,market,sessions=market_fixture(stocks=2,days=4,start='2024-01-02')
    prices['source_hash']='a'*64
    prices.loc[prices.instrument_id=='id-001',['volume','open','high','low']]=0
    start,end=sessions[0].date(),sessions[-1].date()
    event=pd.DataFrame([dict(event_id='later-event',instrument_id='id-000',symbol='STOCK000',
        ex_date=sessions[-1],action_type='SPLIT',parse_status='PARSED',ratio_numerator=2,ratio_denominator=1,cash_amount=None)])
    write_daily(prices,config.prices_dir)
    write_daily(adjust_prices(prices,event),tmp_path/'normalized/adjusted_prices')
    market['high']=market[['open','close']].max(axis=1)*1.01
    market['low']=market[['open','close']].min(axis=1)*.99
    write_daily(pd.concat([market.assign(index_name=name) for name in ('NIFTY 50','NIFTY 500')]),tmp_path/'normalized/indices')
    write_parquet(event,tmp_path/'normalized/corporate_actions/events.parquet')
    write_parquet(pd.DataFrame(dict(instrument_id=['id-000'],identity_status='RESOLVED',valid_from=sessions[0],
        valid_to=sessions[-1])),tmp_path/'normalized/security_history/identities.parquet')
    ledger=PipelineState(config)
    ledger.record('nse_corporate_actions',status='READY',checked_from=str(start),checked_through=str(end))
    ledger.record('adjusted_prices',status='READY',corporate_action_version=action_version(event),**{'from':str(start),'to':str(end)})
    monkeypatch.setattr('quant.pipeline.check_research_ready.read_calendar',lambda cfg,a,b:
        pd.DataFrame(dict(trade_date=sessions[sessions<=pd.Timestamp(b)],is_trading_session=True)))
    monkeypatch.setattr('quant.pipeline.check_research_ready.audit_prices',lambda cfg,a,b,**kwargs:
        dict(status='READY',coverage_percent=100,latest_date=str(b)))
    assert check_research_ready(config,as_of=sessions[1].date(),history_start=start)['status']=='READY'
    first_path=tmp_path/f'normalized/adjusted_prices/year={start.year}/month={start.month:02d}/{start}.parquet'
    original=pd.read_parquet(first_path)
    unresolved=original.copy(); unresolved['instrument_id']=None
    unresolved['adjustment_status']='UNRESOLVED_IDENTITY'
    write_parquet(unresolved,first_path)
    result=check_research_ready(config,as_of=sessions[1].date(),history_start=start)
    assert not result['identity_ready'] and result['errors']['historical_identity']['sessions_without_resolved_EQ']==1
    write_parquet(original,first_path)
    ledger.record('adjusted_prices',status='READY',**{'from':str(sessions[1].date())})
    assert not check_research_ready(config,as_of=sessions[1].date(),history_start=start)['adjustments_ready']
    ledger.record('adjusted_prices',status='READY',**{'from':str(start)})
    # A forged executable status must not allow an unresolved action into signals.
    event['parse_status']='NEEDS_REVIEW'
    write_parquet(event,tmp_path/'normalized/corporate_actions/events.parquet')
    ledger.record('adjusted_prices',status='READY',corporate_action_version=action_version(event))
    result=check_research_ready(config,as_of=end,history_start=start)
    assert not result['adjustments_ready'] and 'unresolved_action_exclusion' in result['errors']


def test_identity_audit_never_borrows_future_isins(tmp_path,monkeypatch):
    from quant.pipeline.audit_identities import audit_identities
    from quant.tests.research_fixtures import market_fixture
    from quant.data.normalization import write_daily
    prices,_,sessions=market_fixture(stocks=2,days=3,start='2010-01-04')
    prices['isin']=prices.symbol.map({'STOCK000':'INE000A01000','STOCK001':'INE000B01000'})
    prices.loc[prices.trade_date==sessions[0],'isin']=None
    prices['source_file']='https://nsearchives.nseindia.com/official-example.zip'
    prices['source_hash']='a'*64
    config=Config(data_dir=tmp_path)
    write_daily(prices,config.prices_dir)
    monkeypatch.setattr('quant.pipeline.audit_identities.read_calendar',lambda *args:
        pd.DataFrame(dict(trade_date=sessions,is_trading_session=True)))
    result=audit_identities(config,sessions[0].date(),sessions[-1].date())
    assert result['status']=='NOT_READY' and result['sessions_without_resolved_EQ']==1
    assert result['first_resolved_session']==str(sessions[1].date())
    assert result['by_year'][0]['resolved_rows']==4 and result['by_year'][0]['unresolved_rows']==2
    assert result['missing_identity_sessions'][0]['source_sha256']=='a'*64
