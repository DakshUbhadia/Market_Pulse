"""Forward records cannot be rewritten, backfilled or given favorable accounting."""
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict
import json

import pandas as pd
import pytest

from quant.backtest.artifacts import seal_backtest, verify_backtest_seal
from quant.backtest.engine import run_backtest
from quant.backtest.portfolio import PortfolioConfig
from quant.backtest.tests.test_simulation import zero_cost
from quant.forward.signal_store import append_record, freeze_signals, read_signals, content_hash
from quant.forward.shadow_portfolio import update_shadow
from quant.forward.outcome_tracker import track_outcomes
from quant.forward.metrics import forward_metrics
from quant.pipeline.run_forward_signal import run_forward_signal
from quant.config import Config
from quant.tests.research_fixtures import market_fixture, execution_scores
from quant.version import MODEL_VERSION, FEATURE_VERSION


def fixture():
    prices,benchmark,sessions = market_fixture(stocks=1,days=100,start='2024-10-01')
    prices['adjusted_open'] = prices['adjusted_close'] = prices['raw_close'] = 100.
    scores = execution_scores(prices)
    scores = scores[scores.as_of.eq(pd.Timestamp('2024-10-31'))].copy()
    scores['model_version'], scores['feature_version'] = MODEL_VERSION, FEATURE_VERSION
    scores['rank'], scores['universe_size'] = 1, 1
    for name in ('momentum','relative_strength','low_risk','liquidity'):
        scores[name+'_score'] = 0.
    scores['momentum_score'] = scores.raw_score/.4
    return prices,benchmark,sessions,scores


def freeze(root,scores,**kwargs):
    defaults = dict(as_of='2024-10-31',generated_at='2024-10-31T19:00:00+05:30',
        next_open='2024-11-01T09:15:00+05:30',data_as_of='2024-10-31',git_commit='test-commit',
        source_manifest_hash='a'*64,settings=dict(portfolio=asdict(PortfolioConfig(holdings=1,max_weight=1)),
            costs=asdict(zero_cost()),lifecycle_scenario='MANDATORY_ECONOMIC_EVENTS_ONLY'))
    defaults.update(kwargs)
    return freeze_signals(root,scores,**defaults)


def test_signal_batch_is_immutable_and_contains_versioned_contributions(tmp_path):
    _,_,_,scores = fixture()
    path = freeze(tmp_path,scores)
    assert freeze(tmp_path,scores) == path
    original = path.read_bytes()
    with pytest.raises(ValueError,match='Immutable'):
        freeze(tmp_path,scores,generated_at='2024-10-31T20:00:00+05:30')
    assert path.read_bytes() == original
    batches,rows = read_signals(tmp_path)
    assert len(rows)==1 and rows.validation_level.iloc[0] == 'FORWARD_PAPER_ONLY'
    assert set(rows.factor_contributions.iloc[0]) == {'momentum','relative_strength','low_risk','liquidity'}
    assert batches[0]['sha256'] == content_hash({k:v for k,v in batches[0].items() if k!='sha256'})


@pytest.mark.parametrize('time',['2024-10-31T15:29:00+05:30','2024-11-01T09:15:00+05:30',
                                 '2024-11-02T18:00:00+05:30','2024-10-31T19:00:00'])
def test_backdated_or_ambiguous_signal_is_rejected(tmp_path,time):
    *_,scores = fixture()
    with pytest.raises(ValueError,match='timing|frozen'):
        freeze(tmp_path,scores,generated_at=time)
    assert not list(tmp_path.rglob('*.json'))


def test_exclusive_publish_never_overwrites_another_writer(tmp_path):
    path = tmp_path/'one.json'
    def write(value):
        try:
            append_record(path,dict(value=value))
            return value
        except ValueError:
            return None
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(write,range(4)))
    assert len([value for value in results if value is not None]) == 1
    assert json.loads(path.read_text())['value'] in results
    assert not list(tmp_path.glob('*.pending'))


def test_tampered_signal_batch_is_detected(tmp_path):
    *_,scores = fixture()
    path = freeze(tmp_path,scores)
    record = json.loads(path.read_text())
    record['signals'][0]['rank'] = 42
    path.write_text(json.dumps(record))
    with pytest.raises(ValueError,match='checksum'):
        read_signals(tmp_path)


def test_shadow_matches_historical_engine_and_rejects_corrected_nav(tmp_path):
    prices,_,sessions,scores = fixture()
    freeze(tmp_path,scores)
    config = PortfolioConfig(holdings=1,max_weight=1)
    kwargs = dict(as_of='2024-11-04',portfolio=config,cost_model=zero_cost(),
        corporate_actions=pd.DataFrame(),lifecycle=None,lifecycle_scenario='MANDATORY_ECONOMIC_EVENTS_ONLY')
    path = update_shadow(tmp_path,prices,sessions,**kwargs)
    _,frozen = read_signals(tmp_path)
    expected = run_backtest(prices,frozen,sessions,start='2024-10-31',end='2024-11-04',
        portfolio=config,cost_model=zero_cost(),corporate_actions=pd.DataFrame())
    record = json.loads(path.read_text())
    assert record['equity']['nav'] == pytest.approx(expected.equity_curve.nav.iloc[-1])
    assert expected.trades.trade_date.tolist() == [pd.Timestamp('2024-11-01')]
    prices.loc[prices.trade_date.eq(pd.Timestamp('2024-11-04')),'adjusted_close'] = 120.
    with pytest.raises(ValueError,match='NAV changed'):
        update_shadow(tmp_path,prices,sessions,**kwargs)


def test_outcomes_append_only_after_maturity_and_never_change_signal(tmp_path):
    prices,benchmark,sessions,scores = fixture()
    signal = freeze(tmp_path,scores)
    original = signal.read_bytes()
    kwargs = dict(cost_model=zero_cost(),corporate_actions=pd.DataFrame(),lifecycle=None,
                  lifecycle_scenario='MANDATORY_ECONOMIC_EVENTS_ONLY')
    pending = track_outcomes(tmp_path,prices,benchmark,benchmark,sessions,as_of='2024-11-01',**kwargs)
    assert pending == dict(written=0,pending=2,blocked=[])
    report = track_outcomes(tmp_path,prices,benchmark,benchmark,sessions,as_of=sessions[-1],**kwargs)
    assert report == dict(written=2,pending=0,blocked=[])
    paths = list((tmp_path/'outcomes').glob('*/*.json'))
    originals = {path:path.read_bytes() for path in paths}
    again = track_outcomes(tmp_path,prices,benchmark,benchmark,sessions,as_of=sessions[-1],**kwargs)
    assert again['written'] == 0
    assert signal.read_bytes() == original and all(path.read_bytes() == value for path,value in originals.items())
    record = json.loads(paths[0].read_text())
    assert record['entry_date'] == '2024-11-01' and record['entry_price'] == 100.
    assert record['cost_adjusted_return'] == pytest.approx(0.)
    metrics = forward_metrics(tmp_path)
    assert metrics['production_validated'] is False and metrics['outcomes']['63']['matured_outcomes'] == 1


def test_unexpected_delisting_blocks_outcome_without_fabricating_fill(tmp_path):
    prices,benchmark,sessions,scores = fixture()
    freeze(tmp_path,scores)
    prices = prices[prices.trade_date < '2024-11-08']
    report = track_outcomes(tmp_path,prices,benchmark,benchmark,sessions,as_of=sessions[-1],
        cost_model=zero_cost(),corporate_actions=pd.DataFrame(),lifecycle=None,
        lifecycle_scenario='MANDATORY_ECONOMIC_EVENTS_ONLY')
    assert report['written'] == 0 and len(report['blocked']) == 2
    assert not list((tmp_path/'outcomes').glob('*/*.json'))


def test_backtest_completion_seal_detects_partial_and_modified_artifacts(tmp_path):
    with pytest.raises(FileNotFoundError):
        verify_backtest_seal(tmp_path)
    (tmp_path/'metrics.json').write_text('{}')
    seal_backtest(tmp_path)
    verify_backtest_seal(tmp_path)
    (tmp_path/'metrics.json').write_text('{"changed":true}')
    with pytest.raises(ValueError,match='checksum'):
        verify_backtest_seal(tmp_path)


def test_forward_pipeline_refuses_a_past_session_before_building_signals(tmp_path,monkeypatch):
    from quant.pipeline import run_forward_signal as module
    days = pd.bdate_range('2024-10-01',periods=40)
    monkeypatch.setattr(module,'read_calendar',lambda *a:pd.DataFrame(dict(trade_date=days,is_trading_session=True)))
    monkeypatch.setattr(module,'require_completed_baselines',lambda *a:{'PRICE':dict(date_range={'to':'2024-10-30'})})
    monkeypatch.setattr(module,'next_session_open',lambda *a:(pd.Timestamp('2024-11-01T09:15:00+05:30'),{}))
    with pytest.raises(ValueError,match='Historical'):
        run_forward_signal(Config(data_dir=tmp_path),pd.Timestamp('2024-10-31').date(),
            price_baseline=tmp_path/'missing',total_return_baseline=tmp_path/'missing',
            now='2024-11-02T19:00:00+05:30',refresh=False)
    assert not list(tmp_path.rglob('*.json'))


def test_forward_daily_pipeline_freezes_then_updates_same_engine_shadow(tmp_path,monkeypatch):
    from quant.pipeline import run_forward_signal as module
    from quant.pipeline import update_forward_outcomes as updater
    from quant.storage.parquet_store import write_parquet
    from quant.storage.research_store import digest_file, write_json
    prices,benchmark,sessions,scores = fixture()
    as_of = pd.Timestamp('2024-10-31').date()
    feature = tmp_path/'features/snapshot.parquet'
    write_parquet(scores,feature)
    write_json(feature.with_suffix('.manifest.json'),dict(files=[],git_commit='synthetic',
        feature_version=FEATURE_VERSION,feature_sha256=digest_file(feature)))
    monkeypatch.setattr(module,'require_completed_baselines',lambda *a:{'PRICE':dict(date_range={'to':'2024-10-30'})})
    monkeypatch.setattr(module,'read_calendar',lambda *a:pd.DataFrame(dict(trade_date=sessions,is_trading_session=True)))
    monkeypatch.setattr(module,'next_session_open',lambda *a:(pd.Timestamp('2024-11-01T09:15:00+05:30'),{}))
    monkeypatch.setattr(module,'require_research_ready',lambda *a:dict(status='SYNTHETIC_ONLY'))
    monkeypatch.setattr(updater,'require_research_ready',lambda *a:dict(status='SYNTHETIC_ONLY'))
    monkeypatch.setattr('quant.pipeline.build_features.build_features',lambda *a:(scores,feature))
    monkeypatch.setattr('quant.pipeline.run_factor_v1.run_factor_v1',lambda *a:(scores,tmp_path/'rank.parquet'))
    for mod in (module,updater):
        monkeypatch.setattr(mod,'load_research_data',lambda *a:(prices,benchmark,sessions,None,benchmark))
        monkeypatch.setattr(mod,'query_dataset',lambda root,name,**kw:pd.DataFrame() if name=='corporate_actions'
            else benchmark.assign(index_name='NIFTY 500 TRI'))
    result = run_forward_signal(Config(data_dir=tmp_path),as_of,price_baseline=tmp_path/'price',
        total_return_baseline=tmp_path/'total',refresh=False,now='2024-10-31T19:00:00+05:30')
    assert result['status'] == 'PAPER_ONLY' and result['outcomes']['pending'] == 2
    original = (tmp_path/'forward/factor_v1/signals/2024-10-31.json').read_bytes()
    repeated = run_forward_signal(Config(data_dir=tmp_path),as_of,price_baseline=tmp_path/'price',
        total_return_baseline=tmp_path/'total',refresh=False,now='2024-10-31T20:00:00+05:30')
    assert repeated['status'] == 'PAPER_ONLY'
    assert (tmp_path/'forward/factor_v1/signals/2024-10-31.json').read_bytes() == original


def test_next_open_uses_official_calendar_and_rejects_ambiguous_special_hours(tmp_path,monkeypatch):
    from quant.forward import calendar
    frame = pd.DataFrame(dict(trade_date=pd.to_datetime(['2024-11-01','2024-11-04']),
        is_trading_session=[False,True],session_type='NORMAL',needs_investigation=False,
        calendar_source_url='https://www.nseindia.com/api/holiday-master',calendar_raw_sha256='a'*64))
    monkeypatch.setattr(calendar,'read_calendar',lambda *a:frame)
    open_,evidence = calendar.next_session_open(Config(data_dir=tmp_path),pd.Timestamp('2024-10-31').date())
    assert open_ == pd.Timestamp('2024-11-04T09:15:00+05:30')
    assert evidence['calendar_raw_sha256'] == 'a'*64
    frame.loc[1,'session_type'] = 'SPECIAL'
    with pytest.raises(ValueError,match='Special-session'):
        calendar.next_session_open(Config(data_dir=tmp_path),pd.Timestamp('2024-10-31').date())


def test_paper_gate_checks_completed_baseline_policy_and_cost_parity(tmp_path):
    from quant.forward.gate import require_completed_baselines
    from quant.backtest.costs import CostModel
    from quant.storage.research_store import write_json, clean_json
    from quant.version import (COST_MODEL_VERSION, EVIDENCE_POLICY_VERSION,
                               LIFECYCLE_POLICY_VERSION, PORTFOLIO_ACCOUNTING_VERSION)
    for basis in ('PRICE','TOTAL_RETURN'):
        root = tmp_path/basis
        root.mkdir()
        manifest = dict(return_basis=basis,date_range={'from':'2016-01-01','to':'2024-10-30'},
            model_version=MODEL_VERSION,feature_version=FEATURE_VERSION,cost_model_version=COST_MODEL_VERSION,
            evidence_policy_version=EVIDENCE_POLICY_VERSION,lifecycle_policy_version=LIFECYCLE_POLICY_VERSION,
            portfolio_accounting_version=PORTFOLIO_ACCOUNTING_VERSION,
            lifecycle_scenario='MANDATORY_ECONOMIC_EVENTS_ONLY',portfolio_settings=clean_json(PortfolioConfig()),
            cost_settings=clean_json(vars(CostModel())))
        write_json(root/'config.json',manifest)
        for name in ('ic.parquet','deciles.parquet','benchmarks.json','equity_curve.parquet','holdings.parquet',
                     'trades.parquet','lifecycle.parquet','baseline-comparison.json','cluster-exposure.json',
                     'IC-confidence-interval.json'):
            (root/name).write_text('synthetic-only')
        write_json(root/'metrics.json',dict(evidence=dict(status='NOT_VALIDATED')))
        write_json(root/'v1-decision.json',dict(decision='GO_FURTHER_V1_RESEARCH'))
        write_json(root/'lifecycle-audit.json',dict(status='EVIDENCE_ONLY',held_event_assessment='ASSESSED',held_events_unresolved=0))
        write_json(root/'robustness.json',dict(cost_1_5x={},cost_2x={}))
        write_json(root/'walk_forward/2024/run-test/metrics.json',{})
        seal_backtest(root)
    config = Config(data_dir=tmp_path)
    assert set(require_completed_baselines(config,tmp_path/'PRICE',tmp_path/'TOTAL_RETURN')) == {'PRICE','TOTAL_RETURN'}
    import shutil
    changed_run = tmp_path/'CHANGED_TOTAL_RETURN'
    shutil.copytree(tmp_path/'TOTAL_RETURN',changed_run,ignore=shutil.ignore_patterns('completion.json'))
    path = changed_run/'config.json'
    changed = json.loads(path.read_text())
    changed['cost_settings']['slippage_bps'] += 1
    write_json(path,changed)
    seal_backtest(path.parent)
    with pytest.raises(ValueError,match='costs differ'):
        require_completed_baselines(config,tmp_path/'PRICE',changed_run)
    failed_run = tmp_path/'FAILED_PRICE'
    shutil.copytree(tmp_path/'PRICE',failed_run,ignore=shutil.ignore_patterns('completion.json'))
    write_json(failed_run/'v1-decision.json',dict(decision='NO_GO_INVESTIGATE'))
    seal_backtest(failed_run)
    with pytest.raises(ValueError,match='go/no-go'):
        require_completed_baselines(config,failed_run,tmp_path/'TOTAL_RETURN')


def test_completion_seal_cannot_be_replaced_after_artifact_changes(tmp_path):
    (tmp_path/'metrics.json').write_text('original')
    seal_backtest(tmp_path)
    original = (tmp_path/'completion.json').read_bytes()
    seal_backtest(tmp_path)
    (tmp_path/'metrics.json').write_text('changed')
    with pytest.raises(ValueError,match='Immutable'):
        seal_backtest(tmp_path)
    assert (tmp_path/'completion.json').read_bytes() == original


def test_policy_change_is_rejected_before_new_signal_and_new_cohort_remains_separate(tmp_path):
    from quant.forward.cohort import cohort_root
    config = Config(data_dir=tmp_path)
    first, second = cohort_root(config,'v1-original'),cohort_root(config,'v1-next')
    *_, scores = fixture()
    original = freeze(first,scores)
    original_bytes = original.read_bytes()
    scores['as_of'] = pd.Timestamp('2024-11-04')
    settings = dict(portfolio=asdict(PortfolioConfig(holdings=1,max_weight=1,initial_cash=2e6)),
        costs=asdict(zero_cost()),lifecycle_scenario='MANDATORY_ECONOMIC_EVENTS_ONLY')
    later = dict(as_of='2024-11-04',generated_at='2024-11-04T19:00:00+05:30',
        next_open='2024-11-05T09:15:00+05:30',data_as_of='2024-11-04',settings=settings)
    with pytest.raises(ValueError,match='Cohort policy changed'):
        freeze(first,scores,**later)
    assert original.read_bytes() == original_bytes and not (first/'signals/2024-11-04.json').exists()
    freeze(second,scores,**later)
    assert len(read_signals(first)[1]) == len(read_signals(second)[1]) == 1
    assert cohort_root(config) == config.data_dir/'forward/factor_v1'
    with pytest.raises(ValueError,match='simple name'):
        cohort_root(config,'../../escape')


def test_competing_policy_writers_cannot_contaminate_one_cohort(tmp_path):
    *_, scores = fixture()
    def writer(cash):
        settings = dict(portfolio=asdict(PortfolioConfig(holdings=1,max_weight=1,initial_cash=cash)),
            costs=asdict(zero_cost()),lifecycle_scenario='MANDATORY_ECONOMIC_EVENTS_ONLY')
        try:
            return freeze(tmp_path,scores,settings=settings)
        except ValueError:
            return None
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(writer,[1e6,2e6]))
    assert sum(value is not None for value in results) == 1
    assert len(read_signals(tmp_path)[1]) == 1
