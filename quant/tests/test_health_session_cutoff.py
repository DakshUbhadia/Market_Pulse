from datetime import date, datetime
from zoneinfo import ZoneInfo
import pandas as pd
import pytest

from quant.config import Config
from quant.data.source_registry import SOURCES
from quant.data.nse_indices import REQUIRED_INDICES
from quant.storage.parquet_store import write_parquet
from quant.storage.research_store import write_json


@pytest.mark.parametrize('stale_master',[False,True])
def test_midnight_health_uses_completed_session_and_acquired_master(tmp_path,monkeypatch,stale_master):
    from quant.pipeline import validate_data as module
    class Clock(datetime):
        @classmethod
        def now(cls,tz=None):
            return cls(2024,7,9,0,15,tzinfo=ZoneInfo('Asia/Kolkata'))
    monkeypatch.setattr(module,'datetime',Clock)
    config = Config(data_dir=tmp_path)
    day = date(2024,7,8)
    calendar = pd.DataFrame(dict(trade_date=[pd.Timestamp(day)],is_trading_session=True,verified=True))
    monkeypatch.setattr(module,'read_calendar',lambda *a:calendar)
    monkeypatch.setattr(module,'audit_prices',lambda *a,**kw:dict(status='READY',missing_sessions=[],coverage_percent=100))
    state = {name:dict(status='READY',last_successful_at='2024-07-08T20:00:00+05:30')
             for name,spec in SOURCES.items() if spec.get('required')}
    master_day = '2024-07-07' if stale_master else '2024-07-08'
    state['nse_security_master'].update(last_success=master_day,last_successful_at=master_day+'T20:00:00+05:30')
    state['nse_corporate_actions'].update(checked_from='2010-01-01',checked_through=str(day))
    state['weekly_integrity'] = dict(status='READY',last_successful_at='2024-07-08T20:00:00+05:30',**{'from':'2010-01-01'})
    write_json(tmp_path/'state/pipeline_state.json',state)
    write_parquet(pd.DataFrame(dict(symbol=['TEST'],series=['EQ'],isin=['INE000000001'])),
                  tmp_path/f'normalized/instruments/nse/{master_day}.parquet')
    write_parquet(pd.DataFrame(dict(symbol=['TEST'],series=['EQ'],identity_status=['RESOLVED'])),
                  tmp_path/'normalized/security_history/identities.parquet')
    for dataset,frame in [
        ('indices',pd.DataFrame([dict(trade_date=pd.Timestamp(day),index_name=name,open=100.,high=101.,low=99.,close=100.) for name in REQUIRED_INDICES])),
        ('vix',pd.DataFrame(dict(trade_date=[pd.Timestamp(day)],close=[15.]))),
        ('adjusted_prices',pd.DataFrame(dict(trade_date=[pd.Timestamp(day)],adjustment_status=['OK'],adjusted_close=[100.],total_return_close=[100.]))),
    ]:
        write_parquet(frame,tmp_path/f'normalized/{dataset}/year=2024/month=07/{day}.parquet')
    result = module.validate_data(config,day,day,incremental=True)
    assert result['freshness_as_of'] == '2024-07-08'
    assert result['status'] == ('NOT_READY' if stale_master else 'READY')
    assert result['sources']['nse_security_master']['status'] == ('STALE' if stale_master else 'READY')
