from datetime import datetime, timezone
import hashlib
import json
import subprocess
import sys
import time

import pandas as pd
import pytest

from quant.features.adjustments import action_version
from quant.features.labels import forward_labels
from quant.backtest.walk_forward import purged_training_labels
from quant.pipeline.export_quant_status import sign_status, status_payload
from quant.pipeline.write_current_status import read_report
from quant.pipeline.state import state_lock
from quant.research.data_interval import certify_data_interval, require_data_interval
from quant.tests.research_fixtures import market_fixture
from quant import version


def test_market_action_digest_has_canonical_nulls():
    actions = pd.DataFrame({'event_id': ['a', 'b'], 'instrument_id': [None, 'stock'],
                            'cash_amount': [None, 15.0]})
    expected = b'[{"event_id":"a","instrument_id":null,"cash_amount":null},{"event_id":"b","instrument_id":"stock","cash_amount":"15.0"}]'
    assert action_version(actions.iloc[::-1]) == hashlib.sha256(expected).hexdigest()


def test_forward_labels_use_exact_calendar_and_keep_missing_population():
    prices, benchmark, sessions = market_fixture(stocks=1, days=70)
    keys = pd.DataFrame({'as_of': [sessions[0], sessions[0], sessions[-1]],
                         'instrument_id': ['id-000', 'absent', 'id-000']})
    labels = forward_labels(prices, benchmark, sessions, signal_keys=keys)
    assert labels.label_available.tolist() == [True, False, False]
    assert labels.entry_at.iloc[0] == sessions[1]
    assert labels.label_end_at.iloc[0] == labels.label_available_at.iloc[0] == sessions[63]
    assert labels.maturity_status.tolist() == ['MATURE', 'IMMATURE', 'MISSING_SIGNAL_OBSERVATION']
    bad = benchmark.copy()
    bad.loc[bad.trade_date.eq(sessions[1]), 'open'] = -1
    rejected = forward_labels(prices, bad, sessions, signal_keys=keys)
    assert rejected.maturity_status.iloc[0] == 'INVALID_BENCHMARK'
    assert pd.isna(rejected.label_available_at.iloc[0])
    assert pd.isna(rejected.future_volatility_63.iloc[0])


def test_joint_interval_rejects_marginal_pass_and_input_tampering():
    dates = pd.date_range('2024-01-31', periods=12, freq='ME').strftime('%Y-%m-%d')
    filings = dict(frequency='monthly',
        periods=[dict(as_of=d, coverage_pct=90, top_liquidity_coverage_pct=92) for d in dates])
    shares = dict(periods=[dict(as_of=d, verified_share_coverage=91, top100_verified_share_coverage=95) for d in dates])
    matrix = dict(periods=[dict(as_of=d, joint_overall_pct=80, joint_top100_pct=90) for d in dates])
    passed = certify_data_interval(filings, shares, matrix=matrix)
    assert passed['joint_matrix']['status'] == 'THRESHOLDS_MET'
    require_data_interval(passed, filings, shares, matrix=matrix)
    matrix['periods'][6]['joint_top100_pct'] = 89
    blocked = certify_data_interval(filings, shares, matrix=matrix)
    assert blocked['certified'] and blocked['joint_matrix']['status'] == 'BLOCKED'
    for record in (passed, blocked):
        with pytest.raises(ValueError, match='certified shared'):
            require_data_interval(record, filings, shares, matrix=matrix)


def test_walk_forward_purges_a_label_published_after_its_exit():
    sessions = pd.bdate_range('2024-01-01', periods=8)
    labels = pd.DataFrame({'as_of': [sessions[0]] * 3, 'exit_date': [sessions[2]] * 3,
        'label_available_at': [sessions[2], sessions[6], pd.NaT], 'label_available': [True] * 3})
    window = dict(train_start=sessions[0], train_end=sessions[4], test_start=sessions[5])
    assert purged_training_labels(labels, window, sessions, embargo_sessions=1).index.tolist() == [0]


def test_console_projection_and_corruption_recovery(tmp_path):
    invalid = tmp_path/'damaged.json'
    invalid.write_bytes(b'{partial')
    assert read_report(invalid)['status'] == 'INVALID'
    current = dict(versions={key: getattr(version, key) for key in dir(version) if key.endswith('_VERSION')},
        local_commit='1'*40, human_review_status='PENDING', evaluation_window_admissible=False,
        diagnostic_runs=[dict(metrics={'daily_return': 0.1}, ranking=['secret'])],
        filing_coverage={'report': {'periods': [dict(as_of='2026-10-30', coverage_pct=25.0)]}})
    result = status_payload(current, now=datetime(2026, 11, 25, tzinfo=timezone.utc))
    assert result['coverage'][0]['filing'] == 25 and result['coverage'][0]['joint'] is None
    assert result['humanReview'] == 'PENDING' and result['fallback'] == 'NOT_ADMITTED'
    assert 'secret' not in json.dumps(result) and result['sealHash'] is None
    assert sign_status(result, 'a'*64) == sign_status(result, 'a'*64)
    with pytest.raises(ValueError, match='SIGNING_KEY'):
        sign_status(result, 'short')


def test_market_lock_recovers_after_writer_termination(tmp_path):
    lock = tmp_path/'market-writer.lock'
    child = subprocess.Popen([sys.executable, '-c', '''
from pathlib import Path
import os
import sys
import time
from quant.pipeline.state import state_lock
with state_lock(Path(sys.argv[1])):
    Path(sys.argv[2]).touch()
    for _ in range(400):
        if Path(sys.argv[3]).exists():
            os._exit(23)
        time.sleep(0.025)
    os._exit(24)
''', str(lock), str(tmp_path/'started'), str(tmp_path/'interrupt')])
    try:
        deadline = time.monotonic() + 10
        while not (tmp_path/'started').exists() and child.poll() is None and time.monotonic() < deadline:
            time.sleep(0.025)
        assert (tmp_path/'started').exists()
        (tmp_path/'interrupt').touch()
        assert child.wait(timeout=10) == 23
    finally:
        if child.poll() is None:
            child.kill()
        child.wait(timeout=10)
    with state_lock(lock):
        assert lock.exists()
