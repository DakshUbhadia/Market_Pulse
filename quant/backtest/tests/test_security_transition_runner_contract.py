"""Real engine and diagnostics must agree on a mandatory transition."""
from datetime import date
import pandas as pd
import pytest
from quant.config import Config
from quant.tests.research_fixtures import market_fixture
from quant.identity.tests.test_transitions import event
from quant.storage.parquet_store import write_parquet, read_parquet_file
from quant.backtest.artifacts import verify_backtest_seal


@pytest.mark.parametrize('total_return',[False,True])
def test_verified_transition_runs_through_entire_research_tree(tmp_path,monkeypatch,total_return):
    from quant.pipeline import run_backtest as runner
    prices,benchmark,sessions=market_fixture(stocks=1,days=300,start='2023-01-02')
    day=sessions[-5]
    after=prices.trade_date.ge(day)
    prices.loc[after,'instrument_id']='successor'
    for column in ['adjusted_open','adjusted_high','adjusted_low','adjusted_close','raw_close']:
        prices.loc[after,column] /= 4
    events=event(tmp_path,predecessor_instrument_id='id-000',successor_instrument_id='successor',
        announced_at='2024-01-01T12:00:00+05:30',ex_date=str(day.date()),effective_date=str(day.date()),
        record_date=str(day.date()),credit_date=str(sessions[-4].date()),listing_date=str(sessions[-3].date()),
        first_tradable_date=str(sessions[-3].date()))
    write_parquet(events,tmp_path/'normalized/security_transitions/fixture.parquet')
    indices=pd.concat([benchmark.assign(index_name=n) for n in ['NIFTY 50','NIFTY 500']])
    actions=pd.DataFrame(columns=['event_id','action_type','ex_date','instrument_id','cash_amount','parse_status'])
    monkeypatch.setattr(runner,'require_research_ready',lambda *a:dict(status='SYNTHETIC_TEST_ONLY'))
    monkeypatch.setattr(runner,'require_certified_implementation',lambda *a:dict(scope='SYNTHETIC_TEST_ONLY'))
    monkeypatch.setattr(runner,'load_research_data',lambda *a:(prices,benchmark,sessions,None,indices))
    monkeypatch.setattr(runner,'query_dataset',lambda root,name,**kw: actions if name=='corporate_actions' else indices.assign(index_name=indices.index_name+' TRI'))
    # Real manifests, feature construction, engine, all 13 stress scenarios,
    # walk-forward, artifact writers and seal remain active.
    path,_=runner.run_research(Config(data_dir=tmp_path),date(2024,1,2),sessions[-1].date(),
        estimate_historical_costs=True,full_robustness=True,total_return=total_return)
    verify_backtest_seal(path)
    ledger=read_parquet_file(path/'security-transitions.parquet')
    assert len(ledger)==1
    assert ledger.pending_units.iloc[0]>0 and ledger.tradable_units.iloc[0]==0
    assert ledger.raw_share_entitlement.iloc[0]>0
    assert ledger.recommendation_instrument_id.iloc[0]=='id-000'
    import json
    assert len(json.loads((path/'robustness.json').read_text()))==13
    windows=list((path/'walk_forward').glob('*/run-*/security-transitions.parquet'))
    assert windows and all(len(read_parquet_file(p))==1 for p in windows)
    assert (path/'dividends.parquet').exists()
