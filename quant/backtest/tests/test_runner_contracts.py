"""Exercise accounting/policy propagation across every orchestration path."""
from datetime import date
from types import SimpleNamespace

import pandas as pd
import pytest

from quant.tests.research_fixtures import market_fixture
from quant.config import Config
from quant.backtest.portfolio import PortfolioConfig
from quant.backtest.costs import CostModel


@pytest.mark.parametrize('total_return',[False,True])
def test_research_runner_accounting_contract(tmp_path,monkeypatch,total_return):
    from quant.pipeline import run_backtest as runner
    prices,benchmark,sessions = market_fixture(stocks=3,days=300,start='2023-01-02')
    indices = pd.concat([benchmark.assign(index_name=name) for name in ('NIFTY 50','NIFTY 500')])
    actions = pd.DataFrame(columns=['event_id','action_type','ex_date','instrument_id','cash_amount','parse_status'])
    tri = indices.assign(index_name=indices.index_name+' TRI')
    monkeypatch.setattr(runner,'require_research_ready',lambda *a:dict(status='SYNTHETIC_TEST_ONLY'))
    monkeypatch.setattr(runner,'require_certified_implementation',lambda *a:dict(scope='SYNTHETIC_TEST_ONLY'))
    monkeypatch.setattr(runner,'input_manifest',lambda *a:dict(files=[],input_sha256='synthetic'))
    monkeypatch.setattr(runner,'load_research_data',lambda *a:(prices,benchmark,sessions,None,indices))
    monkeypatch.setattr(runner,'query_dataset',lambda root,name,**kw: actions if name=='corporate_actions' else tri)
    calls=[]
    real = runner.run_backtest
    def simulation(*args,**kwargs):
        calls.append(kwargs)
        return real(*args,**kwargs)
    monkeypatch.setattr(runner,'run_backtest',simulation)
    for name in ('robustness_runs','walk_forward'):
        original = getattr(runner,name)
        def wrapper(*args,_original=original,_name=name,**kwargs):
            calls.append(dict(path=_name,**kwargs))
            return _original(*args,**kwargs)
        monkeypatch.setattr(runner,name,wrapper)
    path,_ = runner.run_research(Config(data_dir=tmp_path),date(2024,1,2),sessions[-1].date(),
        estimate_historical_costs=True,full_robustness=True,total_return=total_return)
    assert {'robustness_runs','walk_forward'} <= {row.get('path') for row in calls}
    if total_return:
        pd.testing.assert_frame_equal(calls[0]['corporate_actions'],actions)
        assert all(row['corporate_actions'] is calls[0]['corporate_actions'] for row in calls)
    else:
        assert all(row['corporate_actions'] is None for row in calls)
    assert all(row['lifecycle_scenario'] == 'MANDATORY_ECONOMIC_EVENTS_ONLY' for row in calls)
    assert (path/'baseline-comparison.json').exists() and (path/'cluster-sensitivity.parquet').exists()
    experiment = next((tmp_path/'research/experiments').iterdir())
    assert (experiment/'prepared-scores.parquet').exists() and (experiment/'prepared-universe.parquet').exists()
    assert not (experiment/'completion.json').exists()


def test_total_return_robustness_forwards_actions_to_every_variant(monkeypatch):
    from quant.backtest import robustness as module
    actions,events = pd.DataFrame({'sentinel':[1]}),pd.DataFrame({'sentinel':[2]})
    dates = pd.bdate_range('2024-01-01',periods=4)
    curve = pd.DataFrame(dict(trade_date=dates,nav=1e6,daily_return=[0,.01,-.01,.005],turnover=0.))
    calls=[]
    def simulate(*args,**kwargs):
        calls.append(kwargs)
        return SimpleNamespace(equity_curve=curve,trades=pd.DataFrame())
    monkeypatch.setattr(module,'run_backtest',simulate)
    monkeypatch.setattr(module,'build_feature_matrix',lambda *a,**k:pd.DataFrame())
    monkeypatch.setattr(module,'score_factor_v1',lambda frame:frame)
    from quant.universe.config import UniverseConfig
    result = module.robustness_runs(pd.DataFrame(),pd.DataFrame(),pd.Series(0.,index=dates),dates,
        start=dates[0],end=dates[-1],portfolio=PortfolioConfig(),cost_model=CostModel(),
        universe_config=UniverseConfig(),benchmark_frame=pd.DataFrame(),corporate_actions=actions,lifecycle_events=events)
    assert len(result) == len(calls) == 13
    assert all(row['corporate_actions'] is actions and row['lifecycle_events'] is events for row in calls)


def test_total_return_walk_forward_preserves_actions_and_policy(monkeypatch):
    from quant.backtest.walk_forward import walk_forward
    actions = pd.DataFrame({'sentinel':[1]})
    dates = pd.bdate_range('2024-01-01',periods=4)
    calls=[]
    def simulate(*a,**kw):
        calls.append(kw)
        return object()
    monkeypatch.setattr('quant.backtest.engine.run_backtest',simulate)
    labels = pd.DataFrame(columns=['as_of','exit_date','label_available'])
    scores = pd.DataFrame(dict(as_of=dates,instrument_id='a'))
    window=dict(train_start=date(2018,1,1),train_end=date(2023,12,31),test_start=date(2024,1,1),test_end=date(2024,12,31))
    walk_forward(pd.DataFrame(),scores,labels,dates,windows=[window],corporate_actions=actions,
                 lifecycle_scenario='KNOWN_EVENT_NEXT_OPEN_EXIT')
    assert len(calls)==1 and calls[0]['corporate_actions'] is actions
    assert calls[0]['lifecycle_scenario'] == 'KNOWN_EVENT_NEXT_OPEN_EXIT'


@pytest.mark.parametrize('module_name',['robustness','walk_forward'])
def test_documented_lifecycle_keyword_reaches_each_simulation(monkeypatch,module_name):
    from quant.backtest import robustness, walk_forward
    from quant.universe.config import UniverseConfig
    module = robustness if module_name == 'robustness' else walk_forward
    actions,events = pd.DataFrame({'action':[1]}),pd.DataFrame({'event':[2]})
    dates = pd.bdate_range('2024-01-01',periods=4)
    calls = []
    curve = pd.DataFrame(dict(trade_date=dates,nav=1e6,daily_return=0.,turnover=0.))
    def simulation(*args,**kwargs):
        calls.append(kwargs)
        return SimpleNamespace(equity_curve=curve,trades=pd.DataFrame())
    if module_name == 'robustness':
        monkeypatch.setattr(module,'run_backtest',simulation)
        monkeypatch.setattr(module,'build_feature_matrix',lambda *a,**k:pd.DataFrame())
        monkeypatch.setattr(module,'score_factor_v1',lambda f:f)
        module.robustness_runs(pd.DataFrame(),pd.DataFrame(),pd.Series(0.,index=dates),dates,
            start=dates[0],end=dates[-1],portfolio=PortfolioConfig(),cost_model=CostModel(),
            universe_config=UniverseConfig(),benchmark_frame=pd.DataFrame(),lifecycle_events=events,corporate_actions=actions)
        assert len(calls) == 13
    else:
        monkeypatch.setattr('quant.backtest.engine.run_backtest',simulation)
        module.walk_forward(pd.DataFrame(),pd.DataFrame(dict(as_of=dates)),
            pd.DataFrame(columns=['as_of','exit_date','label_available']),dates,
            windows=[dict(train_start=date(2018,1,1),train_end=date(2023,12,31),
                          test_start=date(2024,1,1),test_end=date(2024,12,31))],
            lifecycle_events=events,corporate_actions=actions)
        assert len(calls) == 1
    assert all(row['lifecycle_events'] is events and row['corporate_actions'] is actions for row in calls)
