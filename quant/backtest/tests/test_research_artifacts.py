"""Synthetic orchestration checks; results are never evidence about NSE returns."""
import json
from datetime import date

import pandas as pd
import pytest

from quant.config import Config
from quant.pipeline import run_backtest as runner
from quant.pipeline.build_adjusted import _build_partitions, _incremental_partitions, action_fingerprints
from quant.features.adjustments import adjust_prices
from quant.features.returns import calculate_returns
from quant.data.normalization import write_daily
from quant.tests.research_fixtures import market_fixture
from quant.backtest.benchmarks import baseline_target
from quant.backtest.portfolio import PortfolioConfig


def test_disk_adjustment_batches_equal_identity_adjustments(tmp_path):
    config = Config(data_dir=tmp_path)
    prices, _, sessions = market_fixture(stocks=2, days=8)
    prices = prices.drop(columns=['instrument_id'])
    prices['isin'] = prices.symbol.map({'STOCK000':'INE000A01000','STOCK001':'INE000B01000'})
    prices['source_hash'] = 'a'*64
    actions = pd.DataFrame()
    write_daily(prices, config.prices_dir)
    rows, partitions, excluded = _build_partitions(config, sessions[0].date(), sessions[-1].date(), actions)
    actual = pd.concat([pd.read_parquet(path) for path in (tmp_path/'normalized/adjusted_prices').rglob('*.parquet')])
    expected = calculate_returns(adjust_prices(prices, actions))
    keys = ['instrument_id','series','trade_date']
    fields = keys + ['adjusted_open','adjusted_close','adjusted_return','source_price_sha256']
    pd.testing.assert_frame_equal(actual[fields].sort_values(keys).reset_index(drop=True),
        expected[fields].sort_values(keys).reset_index(drop=True))
    assert (rows, partitions, excluded) == (16,8,[])


def test_liquid_baseline_population_is_independent_of_factor_completeness():
    rows = pd.DataFrame(dict(instrument_id=['a','b'],eligible=True,feature_valid=[True,False],vol_63=.2))
    weights = baseline_target('liquid_equal_weight')(rows,{},PortfolioConfig())
    assert set(weights.index)=={'a','b'}


def test_incremental_action_rebases_older_prices_and_keeps_return_seam(tmp_path):
    from quant.data.security_history import attach_identities, build_security_history
    from quant.storage.parquet_store import write_parquet
    config = Config(data_dir=tmp_path)
    prices,_,sessions=market_fixture(stocks=2,days=8)
    prices=prices.drop(columns='instrument_id')
    prices['isin']=prices.symbol.map({'STOCK000':'INE000A01000','STOCK001':'INE000B01000'})
    prices['source_hash']='a'*64
    write_daily(prices,config.prices_dir)
    initial=calculate_returns(adjust_prices(prices[prices.trade_date<=sessions[5]],pd.DataFrame()))
    write_daily(initial,tmp_path/'normalized/adjusted_prices')
    write_parquet(build_security_history(prices),tmp_path/'normalized/security_history/identities.parquet')
    identity=attach_identities(prices).instrument_id.iloc[0]
    actions=pd.DataFrame([dict(event_id='new-bonus',instrument_id=identity,symbol='STOCK000',
        ex_date=sessions[6],action_type='BONUS',parse_status='PARSED',ratio_numerator=1,ratio_denominator=1,cash_amount=None)])
    prior={'from':str(sessions[0].date()),'action_fingerprints':{}}
    _incremental_partitions(config,sessions[4].date(),sessions[-1].date(),actions,prior,action_fingerprints(actions))
    actual=pd.concat([pd.read_parquet(path) for path in (tmp_path/'normalized/adjusted_prices').rglob('*.parquet')])
    expected=calculate_returns(adjust_prices(prices,actions))
    keys=['instrument_id','series','trade_date']
    fields=keys+['adjusted_open','adjusted_close','adjusted_return','total_return_close']
    pd.testing.assert_frame_equal(actual[fields].sort_values(keys).reset_index(drop=True),
        expected[fields].sort_values(keys).reset_index(drop=True))


def test_full_research_runner_writes_reproducible_artifact_contract(tmp_path, monkeypatch):
    prices, benchmark, sessions = market_fixture(stocks=35, days=440, start='2023-01-02')
    indices = pd.concat([benchmark.assign(index_name=name) for name in ('NIFTY 50','NIFTY 500')])
    monkeypatch.setattr(runner,'require_research_ready',lambda *args: {'status':'SYNTHETIC_TEST_ONLY'})
    monkeypatch.setattr(runner,'load_research_data',lambda *args: (prices,benchmark,sessions,None,indices))
    monkeypatch.setattr(runner,'input_manifest',lambda *args: dict(input_sha256='synthetic',git_commit='test',files=[]))
    path,evidence=runner.run_research(Config(data_dir=tmp_path),date(2024,1,2),sessions[-1].date(),
        estimate_historical_costs=True,full_robustness=False)
    assert evidence['status']=='NOT_VALIDATED'
    for name in ('config.json','metrics.json','equity_curve.parquet','trades.parquet','holdings.parquet',
                 'skipped_orders.parquet','ic.parquet','deciles.parquet','report.md','robustness.json',
                 'benchmarks.json','IC-confidence-interval.json','ranking-top30.json'):
        assert (path/name).is_file()
    manifest=json.loads((path/'config.json').read_text())
    assert manifest['return_basis']=='PRICE' and manifest['cost_settings']['allow_estimated_history']
    assert len(json.loads((path/'benchmarks.json').read_text()))==5
    assert list((path/'walk_forward/2024').glob('run-*/metrics.json'))
    curve=pd.read_parquet(path/'equity_curve.parquet')
    assert curve.nav.gt(0).all() and curve.cash.ge(-1e-7).all()
