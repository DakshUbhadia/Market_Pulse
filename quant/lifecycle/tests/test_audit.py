from datetime import date

import pandas as pd
import pytest

from quant.config import Config
from quant.pipeline.audit_lifecycle import audit_lifecycle
from quant.backtest.engine import run_backtest
from quant.lifecycle.policy import DEFAULT_LIFECYCLE_SCENARIO
from quant.tests.research_fixtures import market_fixture,execution_scores
from quant.backtest.tests.test_simulation import zero_cost
from quant.backtest.tests.test_lifecycle import event
from quant.lifecycle.schema import normalize_events


def test_missing_coverage_and_unassessed_holdings_cannot_imply_readiness(tmp_path):
    result = audit_lifecycle(Config(data_dir=tmp_path),as_of=date(2024,1,1),write=False)
    assert not result['lifecycle_data_ready'] and result['lifecycle_coverage_start'] is None
    assert result['unresolved_held_lifecycle_events'] is None
    assert result['held_valuation_assessment'] == 'UNASSESSED'


def test_actual_unvalued_holding_blocks_lifecycle_audit(tmp_path):
    held = pd.DataFrame(dict(trade_date=[pd.Timestamp('2024-01-01')],instrument_id=['a'],value=[float('nan')]))
    report = audit_lifecycle(Config(data_dir=tmp_path),as_of=date(2024,1,1),holdings=held,write=False)
    assert report['status'] == 'BLOCKED' and report['unresolved_held_lifecycle_events'] == 1


def test_strict_primary_policy_cannot_silently_select_risk_exit():
    assert DEFAULT_LIFECYCLE_SCENARIO == 'MANDATORY_ECONOMIC_EVENTS_ONLY'
    prices,_,dates = market_fixture(stocks=1,days=40,start='2024-10-01')
    scores = execution_scores(prices)
    prices = prices[prices.trade_date < '2024-11-08']
    with pytest.raises(ValueError,match='Unvalued holding'):
        run_backtest(prices,scores,dates,cost_model=zero_cost(),lifecycle_events=normalize_events([event()]))


def test_verified_evidence_is_pit_audited_and_raw_mutation_blocks(tmp_path):
    import json
    from pathlib import Path
    from quant.data.http import sha256
    from quant.storage.parquet_store import write_parquet
    config = Config(data_dir=tmp_path)
    fixture = Path(__file__).parents[2]/'backtest/tests/fixtures/essaroil_suspension.json'
    record = json.loads(fixture.read_text())
    raw = tmp_path/'raw/notice.json'
    raw.parent.mkdir()
    raw.write_bytes(b'official evidence fixture')
    record.update(raw_path='raw/notice.json',source_sha256=sha256(raw.read_bytes()))
    write_parquet(normalize_events([record]),tmp_path/'normalized/lifecycle/events.parquet')
    before = audit_lifecycle(config,as_of=date(2016,1,26),write=False)
    assert before['verified_events'] == 0
    after = audit_lifecycle(config,as_of=date(2016,1,28),write=False)
    assert after['verified_events'] == 1 and after['status'] == 'EVIDENCE_ONLY'
    assert not after['lifecycle_data_ready']
    raw.write_bytes(b'modified')
    assert audit_lifecycle(config,as_of=date(2016,1,28),write=False)['status'] == 'BLOCKED'


def test_research_manifest_freezes_lifecycle_raw_evidence(tmp_path):
    import json
    from pathlib import Path
    from quant.data.http import sha256
    from quant.storage.parquet_store import write_parquet
    from quant.storage.research_store import input_manifest,verify_manifest
    record = json.loads((Path(__file__).parents[2]/'backtest/tests/fixtures/essaroil_suspension.json').read_text())
    raw = tmp_path/'raw/notice.json'
    raw.parent.mkdir()
    raw.write_bytes(b'source bytes')
    record.update(raw_path='raw/notice.json',source_sha256=sha256(raw.read_bytes()))
    write_parquet(normalize_events([record]),tmp_path/'normalized/lifecycle/events.parquet')
    config = Config(data_dir=tmp_path)
    manifest = input_manifest(config,date(2016,1,28))
    assert any(item['path'].replace('\\','/') == 'raw/notice.json' for item in manifest['files'])
    verify_manifest(config,manifest)
    raw.write_bytes(b'changed source')
    with pytest.raises(ValueError,match='inputs changed'):
        verify_manifest(config,manifest)


def test_held_event_coverage_uses_complete_portfolio_dates_and_blocks_unresolved_economics(tmp_path):
    import json
    from pathlib import Path
    from quant.data.http import sha256
    from quant.storage.parquet_store import write_parquet
    config = Config(data_dir=tmp_path)
    record = json.loads((Path(__file__).parents[2]/'backtest/tests/fixtures/essaroil_suspension.json').read_text())
    raw = tmp_path/'raw/notice.json'
    raw.parent.mkdir()
    raw.write_bytes(b'notice evidence fixture')
    record.update(raw_path='raw/notice.json',source_sha256=sha256(raw.read_bytes()))
    events = normalize_events([record])
    write_parquet(events,tmp_path/'normalized/lifecycle/events.parquet')
    day = pd.Timestamp(record['effective_date'])
    dates = pd.bdate_range(end=day,periods=3)
    held = pd.DataFrame(dict(trade_date=[dates[0]],instrument_id=[record['instrument_id']],value=[100.]))
    # The position is gone at the prior session; its stale last row is no proof of ownership.
    report = audit_lifecycle(config,as_of=day.date(),holdings=held,lifecycle_records=pd.DataFrame(),
        portfolio_sessions=dates,write=False)
    assert report['held_events_encountered'] == 0
    held.loc[0,'trade_date'] = dates[-2]
    report = audit_lifecycle(config,as_of=day.date(),holdings=held,lifecycle_records=pd.DataFrame(),
        portfolio_sessions=dates,write=False)
    assert report['held_events_encountered'] == 1 and report['held_events_unresolved'] == 1
    assert report['status'] == 'BLOCKED' and not report['lifecycle_data_ready']
