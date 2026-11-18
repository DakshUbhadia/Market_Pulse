import hashlib
import pandas as pd
import pytest
from quant.identity.transitions import COLUMNS, validate_transitions
from quant.backtest.security_transitions import SecurityTransitions
from quant.lifecycle.state import simulation_time, UnvaluedHolding


def event(tmp_path, **updates):
    (tmp_path/'source').write_bytes(b'official fixture')
    row = dict.fromkeys(COLUMNS)
    row.update(transition_id='split',predecessor_instrument_id='old',successor_instrument_id='new',
        predecessor_isin='OLD',successor_isin='NEW',security_lineage_id='lineage',transition_type='SPLIT_AND_BONUS',
        announced_at='2016-03-01T10:00:00+05:30',ex_date='2016-03-16',record_date='2016-03-17',
        effective_date='2016-03-16',credit_date='2016-03-18',listing_date='2016-03-21',first_tradable_date='2016-03-21',
        raw_share_multiplier=4.,economic_share_multiplier=4.,price_adjustment_multiplier=.25,
        source_exchange='NSE',source_url='https://nsearchives.nseindia.com/fixture',
        source_sha256=hashlib.sha256(b'official fixture').hexdigest(),raw_path='source',
        verification_status='VERIFIED_COMPLETE',evidence_notes='Synthetic accounting fixture, not historical evidence',parser_version='test')
    row.update(updates)
    return pd.DataFrame([row])


def test_pending_cost_basis_and_adjusted_units(tmp_path):
    engine=SecurityTransitions(event(tmp_path),tmp_path)
    positions,basis={'old':10.},{'old':100.}
    day=pd.Timestamp('2016-03-16')
    engine.apply(day,simulation_time(day,'09:15'),positions,basis,
        {'new':{'split_factor':2.}},{'old':{'split_factor':1.}})
    assert positions == {'new':20.}
    assert positions['new']*basis['new'] == 1000.
    assert engine.records[0]['raw_share_entitlement'] == 40.
    assert engine.pending('new',day)==20.
    assert not engine.entry_allowed('old',day,simulation_time(day,'09:15'))
    assert engine.entry_allowed('new',day,simulation_time(day,'09:15'))
    assert engine.pending('new',pd.Timestamp('2016-03-21'))==0
    engine.apply(day,simulation_time(day,'09:15'),positions,basis,{}, {})
    assert positions == {'new':20.}


def test_incomplete_and_future_terms_never_bridge(tmp_path):
    for updates in [dict(verification_status='VERIFIED_TERMS_ONLY'),dict(announced_at='2016-03-16T12:00:00+05:30')]:
        engine=SecurityTransitions(event(tmp_path,**updates),tmp_path)
        positions,basis={'old':10.},{'old':100.}
        day=pd.Timestamp('2016-03-16')
        engine.apply(day,simulation_time(day,'09:15'),positions,basis,{}, {})
        assert positions == {'old':10.}


def test_missing_quote_never_uses_future_price(tmp_path):
    engine=SecurityTransitions(event(tmp_path),tmp_path)
    day=pd.Timestamp('2016-03-16')
    with pytest.raises(UnvaluedHolding):
        engine.apply(day,simulation_time(day,'09:15'),{'old':10.},{'old':100.},{},{'old':{'split_factor':1.}})


@pytest.mark.parametrize('updates',[
    dict(first_tradable_date='2016-03-17'),dict(announced_at='2016-03-01'),
    dict(source_sha256='bad'),dict(economic_share_multiplier=2),dict(raw_path='../escape'),
    dict(transition_type='DEMERGER_CONVERSION')])
def test_unsafe_terms_rejected(tmp_path,updates):
    with pytest.raises(ValueError):
        validate_transitions(event(tmp_path,**updates),tmp_path)


def test_engine_never_sells_pending_units(tmp_path):
    from quant.backtest.engine import run_backtest
    from quant.backtest.portfolio import PortfolioConfig
    from quant.backtest.costs import CostModel
    days=pd.bdate_range('2016-03-14','2016-03-22')
    prices=pd.DataFrame([dict(trade_date=d,instrument_id='old' if d<pd.Timestamp('2016-03-16') else 'new',
        series='EQ',adjusted_open=100. if d<pd.Timestamp('2016-03-16') else 25.,
        adjusted_close=100. if d<pd.Timestamp('2016-03-16') else 25.,split_factor=1.,volume=1000,adjustment_status='OK') for d in days])
    scores=pd.DataFrame([dict(as_of=d,instrument_id='old',percentile_score=100.,raw_score=1.) for d in [days[0],days[1],pd.Timestamp('2016-03-18')]])
    target=lambda selected,positions,config:pd.Series({'old':1.}) if not positions else pd.Series(dtype=float)
    result=run_backtest(prices,scores,days,signal_dates=list(scores.as_of),
        portfolio=PortfolioConfig(holdings=1,max_weight=1),cost_model=CostModel(allow_estimated_history=True),
        target_builder=target,security_transitions=event(tmp_path),transition_data_dir=tmp_path)
    assert len(result.security_transitions)==1
    assert result.holdings.query("instrument_id == 'new'").pending_units.iloc[0]>0
    sales=result.trades[result.trades.side.eq('SELL')]
    assert list(sales.trade_date)==[pd.Timestamp('2016-03-21')]
    assert result.holdings[result.holdings.trade_date.eq(pd.Timestamp("2016-03-18"))].pending_units.iloc[0]>0


def test_transition_manifest_includes_hash_named_partitions(tmp_path):
    from quant.config import Config
    from quant.storage.parquet_store import write_parquet
    from quant.storage.research_store import input_manifest, verify_manifest
    frame=event(tmp_path,verification_status='NEEDS_REVIEW',raw_path=None)
    path=tmp_path/'normalized/security_transitions/z-hash.parquet'
    write_parquet(frame,path)
    config=Config(data_dir=tmp_path)
    manifest=input_manifest(config,'2026-11-17')
    assert str(path.relative_to(tmp_path)) in {r['path'] for r in manifest['files']}
    verify_manifest(config,manifest)
