from pathlib import Path
import pandas as pd
import pytest

from quant.data.nse_client import RawResponse
from quant.data.nse_corporate_actions import parse_corporate_actions
from quant.data.security_history import instrument_id
from quant.features.adjustments import adjust_prices


def test_stale_action_isin_uses_dated_stable_identity_and_removes_false_bonus_loss():
    old,new = 'INE509F01011','INE509F01029'
    history = pd.DataFrame([dict(symbol='CUPID',series='EQ',isin=isin,instrument_id=instrument_id(isin),
        valid_from=pd.Timestamp(start),valid_to=pd.Timestamp(end),identity_status='RESOLVED')
        for isin,start,end in [(old,'2016-01-01','2023-12-12'),(new,'2024-10-28','2026-11-17')]])
    raw = RawResponse('https://www.nseindia.com/api/corporates-corporateActions',
        '2026-11-18T00:00:00+05:30','a'*64,Path('raw.json'),200)
    event = dict(symbol='CUPID',isin=old,exDate='09-Mar-2026',subject='Bonus 4:1')
    actions = parse_corporate_actions([event],raw,history)
    assert actions.instrument_id.iloc[0] == instrument_id(new)
    assert actions.source_instrument_id.iloc[0] == instrument_id(old)
    assert actions.identity_resolution.iloc[0] == 'STALE_SOURCE_ISIN_RECONCILED'
    bars = pd.DataFrame(dict(trade_date=pd.to_datetime(['2026-03-06','2026-03-09']),
        symbol='CUPID',series='EQ',isin=new,instrument_id=instrument_id(new),close=[400.,80.]))
    adjusted = adjust_prices(bars,actions)
    assert adjusted.adjusted_close.tolist() == [80.,80.]
    # A future identity must not be projected onto an earlier action.
    event['exDate'] = '09-Mar-2023'
    earlier = parse_corporate_actions([event],raw,history)
    assert earlier.instrument_id.iloc[0] == instrument_id(old)


def test_action_date_identity_transition_is_never_silently_bridged():
    old,new = 'INE509F01011','INE509F01029'
    history = pd.DataFrame([dict(symbol='CUPID',series='EQ',instrument_id=instrument_id(isin),
        valid_from=pd.Timestamp(start),valid_to=pd.Timestamp(end),identity_status='RESOLVED')
        for isin,start,end in [(old,'2024-01-01','2026-03-08'),(new,'2026-03-09','2026-11-17')]])
    raw = RawResponse('https://www.nseindia.com/api/test','2026-11-18T00:00:00+05:30','a'*64,Path('raw.json'),200)
    actions = parse_corporate_actions([dict(symbol='CUPID',isin=old,exDate='09-Mar-2026',subject='Bonus 4:1')],raw,history)
    assert actions.instrument_id.iloc[0] == instrument_id(old)
    assert actions.identity_resolution.iloc[0] == 'IDENTITY_TRANSITION_UNASSESSED'


def test_reused_symbol_cannot_reassign_an_action_to_a_different_issuer():
    old,new = 'INE509F01011','INE940H01022'
    history = pd.DataFrame([dict(symbol='REUSED',series='EQ',isin=isin,instrument_id=instrument_id(isin),
        valid_from=pd.Timestamp(start),valid_to=pd.Timestamp(end),identity_status='RESOLVED')
        for isin,start,end in [(old,'2020-01-01','2023-01-01'),(new,'2024-01-01','2026-11-17')]])
    raw = RawResponse('https://www.nseindia.com/api/test','2026-11-18T00:00:00+05:30','a'*64,Path('raw.json'),200)
    actions = parse_corporate_actions([dict(symbol='REUSED',isin=old,exDate='09-Mar-2026',subject='Bonus 4:1')],raw,history)
    assert actions.instrument_id.iloc[0] == instrument_id(old)
    assert actions.identity_resolution.iloc[0] == 'SOURCE_IDENTITY_CONFLICT_UNASSESSED'


@pytest.mark.parametrize('old_isin_observed',[False,True])
def test_incremental_repair_proves_reported_isin_absent_before_ignoring_missing_history(tmp_path,old_isin_observed):
    from quant.config import Config
    from quant.pipeline.build_adjusted import _incremental_partitions,action_fingerprints
    from quant.storage.parquet_store import read_parquet_file,write_parquet
    from quant.features.returns import calculate_returns
    from quant.data.normalization import write_daily
    config=Config(data_dir=tmp_path)
    old,new='INE509F01011','INE509F01029'
    dates=pd.to_datetime(['2024-01-01','2024-01-02'])
    bars=pd.DataFrame(dict(trade_date=dates,symbol='CUPID',series='EQ',isin=new,
        open=[400.,80.],high=[400.,80.],low=[400.,80.],close=[400.,80.],
        volume=10.,traded_value=4000.,source_hash='a'*64))
    if old_isin_observed:
        bars=pd.concat([bars,bars.iloc[:1].assign(symbol='PRECURSOR',isin=old)],ignore_index=True)
    write_daily(bars,config.prices_dir)
    history=pd.DataFrame(dict(instrument_id=[instrument_id(new)],isin=[new]))
    write_parquet(history,tmp_path/'normalized/security_history/identities.parquet')
    before=pd.DataFrame([dict(event_id='bonus',instrument_id=instrument_id(old),symbol='CUPID',
        ex_date=dates[1],action_type='BONUS',parse_status='PARSED',ratio_numerator=4.,ratio_denominator=1.,cash_amount=None)])
    write_daily(calculate_returns(adjust_prices(bars,before)),tmp_path/'normalized/adjusted_prices')
    after=before.assign(instrument_id=instrument_id(new),source_instrument_id=instrument_id(old),source_isin=old)
    prior=dict(action_fingerprints=action_fingerprints(before),**{'from':'2024-01-01'})
    if old_isin_observed:
        with pytest.raises(ValueError,match='lacks historical ISIN evidence'):
            _incremental_partitions(config,dates[1].date(),dates[1].date(),after,prior,action_fingerprints(after))
    else:
        _incremental_partitions(config,dates[1].date(),dates[1].date(),after,prior,action_fingerprints(after))
        first=read_parquet_file(tmp_path/'normalized/adjusted_prices/year=2024/month=01/2024-01-01.parquet')
        assert first.adjusted_close.tolist() == [80.]
