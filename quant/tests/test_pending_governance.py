"""Pending governance permits software work while forbidding accepted research evidence."""
from pathlib import Path
import json

import pandas as pd
import pytest

from quant.config import Config, REPO_ROOT
from quant.forward.signal_store import content_hash
from quant.governance.gates import GateRegistry, GovernanceBlocked, GATE_ID, default_gate
from quant.governance.review import require_review, seal_review
from quant.storage.research_store import write_json, digest_file
from quant.tests.governance_fixtures import human_review, approve_test_gate


def transition_review(*, decision='CONFIRM_EVIDENCE_EXHAUSTED_UNRESOLVED', **fields):
    gate = default_gate()
    return human_review('TRANSITION_EXHAUSTION', gate['subject_sha256'], decision,
        subject_id='TIDEWATER_2016', transition_id='TIDEWATER-2016-03-17',
        automated_review_sha256=gate['subject_sha256'], sources_reviewed=['SYNTHETIC TEST SOURCE'],
        facts_proven=['SYNTHETIC TEST FACT'], facts_unproven=['SYNTHETIC MISSING FACT'],
        search_routes_attempted=['SYNTHETIC TEST ROUTE'], **fields)


def test_pending_review_blocks_v1_seal(tmp_path):
    from quant.backtest.artifacts import seal_backtest
    from quant.version import MODEL_VERSION
    write_json(tmp_path/'config.json', dict(model_version=MODEL_VERSION))
    with pytest.raises(GovernanceBlocked) as error:
        seal_backtest(tmp_path)
    assert error.value.gate['status'] == 'PENDING'
    assert not (tmp_path/'completion.json').exists()


def test_pending_review_blocks_forward_cohort(tmp_path):
    from quant.pipeline.run_registered_forward import run_registered_forward
    with pytest.raises(GovernanceBlocked) as error:
        run_registered_forward(Config(data_dir=tmp_path), registry=tmp_path/'registry', model_id='test',
            cohort='test', as_of='2026-11-17', price_baseline=tmp_path/'price', total_return_baseline=tmp_path/'tr')
    assert error.value.outcome == 'BLOCKED_BY_GOVERNANCE'
    assert not (tmp_path/'forward').exists()


def test_pending_and_rejected_are_distinct_and_independent_work_remains_allowed(tmp_path):
    pending = GateRegistry(tmp_path).initialize()
    assert pending['human_review_status'] == 'PENDING'
    assert pending['evaluation_window_admissible'] is False
    registry = GateRegistry(tmp_path)
    path = tmp_path/'rejected.json'
    seal_review(transition_review(decision='REOPEN_SEARCH'), path)
    registry.decide(path)
    rejected = registry.snapshot()
    assert rejected['human_review_status'] == 'REJECTED'
    assert rejected['gates'][GATE_ID]['blocking_reason'] == 'HUMAN_REVIEW_REJECTED'
    for action in ('FILING_DISCOVERY', 'CAPITAL_EVENT_VERIFICATION', 'SHARE_CHAINS', 'V2_DATA_MATRIX',
                   'DIAGNOSTIC_V1', 'DIAGNOSTIC_V2', 'TEST_FORWARD', 'DIAGNOSTIC_RELEASE', 'MONITORING_DRY_RUN'):
        registry.require(action)
    assert GateRegistry().snapshot()['human_review_status'] == 'PENDING'


def test_rejected_review_blocks_fallback(tmp_path):
    registry = approve_test_gate(tmp_path, decision='REOPEN_SEARCH')
    with pytest.raises(GovernanceBlocked) as error:
        registry.require('V1_SEAL')
    assert error.value.gate['status'] == 'REJECTED'
    assert not registry.snapshot()['evaluation_window_admissible']


def test_approved_review_admits_matching_fallback(tmp_path):
    registry = approve_test_gate(tmp_path)
    assert registry.snapshot()['evaluation_window_admissible']
    assert registry.require('V2_SPEC_FREEZE')['human_review_status'] == 'APPROVED'
    from quant.research.evaluation_window import load_evaluation_window
    assert load_evaluation_window(tmp_path/'reports/v1-evaluation-window-admitted.json')['effective_start'] == '2017-03-28'


def test_transition_approval_does_not_automatically_admit_a_window(tmp_path):
    path = tmp_path/'approved.json'
    seal_review(transition_review(), path)
    registry = GateRegistry(tmp_path)
    registry.decide(path)
    assert registry.snapshot()['human_review_status'] == 'APPROVED'
    assert not registry.snapshot()['evaluation_window_admissible']
    with pytest.raises(GovernanceBlocked, match='ADMISSION_PENDING'):
        registry.require('V1_SEAL')


@pytest.mark.parametrize('changes', [dict(subject_id='ANOTHER_SECURITY'), dict(subject_sha256='a'*64),
    dict(automated_review_sha256='a'*64), dict(status='PENDING'), dict(status='REVIEWED'),
    dict(performance_information_used=True)])
def test_review_for_wrong_subject_is_rejected(changes, tmp_path):
    value = transition_review()
    value.update(changes)
    value['sha256'] = content_hash({k: v for k, v in value.items() if k != 'sha256'})
    with pytest.raises(ValueError):
        require_review(value, review_type='TRANSITION_EXHAUSTION', subject_id='TIDEWATER_2016',
            subject_sha256=default_gate()['subject_sha256'], decision='CONFIRM_EVIDENCE_EXHAUSTED_UNRESOLVED')


def test_review_hash_must_match_evidence_packet(tmp_path):
    value = transition_review()
    value['subject_sha256'] = value['automated_review_sha256'] = 'f'*64
    value['sha256'] = content_hash({k: v for k, v in value.items() if k != 'sha256'})
    path = tmp_path/'wrong-packet.json'
    seal_review(value, path)
    with pytest.raises(ValueError, match='bind this subject'):
        GateRegistry(tmp_path).decide(path)
    assert GateRegistry(tmp_path).snapshot()['human_review_status'] == 'PENDING'


def test_pending_final_run_records_governance_outcome_before_any_data_work(tmp_path, monkeypatch):
    from quant.pipeline import run_backtest as runner
    def unexpected(*a, **k):
        raise AssertionError('Pending final research must not access data')
    monkeypatch.setattr(runner, 'require_research_ready', unexpected)
    with pytest.raises(GovernanceBlocked):
        runner.run_research(Config(data_dir=tmp_path), pd.Timestamp('2016-01-01').date(), pd.Timestamp('2026-11-17').date())
    record = json.loads(next((tmp_path/'research/experiments').glob('*/outcome.json')).read_text())
    assert record['outcome'] == 'BLOCKED_BY_GOVERNANCE'
    assert record['governance_status'] == 'PENDING'
    assert record['seal_eligible'] is False


def test_governance_journal_changes_are_detected(tmp_path):
    registry = GateRegistry(tmp_path)
    registry.initialize()
    path = next((tmp_path/'research/governance/events').glob('*.json'))
    record = json.loads(path.read_text())
    record['gate']['status'] = 'APPROVED'
    write_json(path, record)
    with pytest.raises(ValueError, match='journal'):
        registry.snapshot()


def test_governance_review_source_cannot_change_after_approval(tmp_path):
    registry = approve_test_gate(tmp_path)
    gate = registry.snapshot()['gates'][GATE_ID]
    Path(gate['review_artifact']).write_text('{}')
    with pytest.raises(ValueError, match='artifact is missing or changed'):
        registry.require('V1_SEAL')


def test_blocked_outcomes_keep_source_data_and_software_distinct():
    from quant.research.authority import blocked_outcome
    from quant.data.nse_client import NseSourceError
    from quant.lifecycle.state import UnvaluedHolding
    assert blocked_outcome(NseSourceError('HTTP 403', http_status=403)) == 'BLOCKED_BY_SOURCE'
    assert blocked_outcome(FileNotFoundError('Missing prices')) == 'BLOCKED_BY_DATA'
    assert blocked_outcome(UnvaluedHolding('SYNTHETIC', '2024-01-01')) == 'BLOCKED_BY_DATA'
    assert blocked_outcome(ValueError('Exact implementation SHA requires unit CI')) == 'BLOCKED_BY_SOFTWARE'
    assert blocked_outcome(RuntimeError('Arithmetic failed')) == 'BLOCKED_BY_SOFTWARE'


def test_diagnostic_integrity_inventory_cannot_become_a_seal_registry_or_research_release(tmp_path):
    from quant.backtest.artifacts import complete_diagnostic, verify_diagnostic_completion, seal_backtest, verify_backtest_seal
    from quant.research.release import build_diagnostic_release, verify_diagnostic_release, verify_research_release
    from quant.models.registry import ModelRegistry
    root = tmp_path/'diagnostic'
    context = dict(research_authority='DIAGNOSTIC_ONLY', seal_eligible=False,
        historical_validation=False, promotion_eligible=False, governance_status='PENDING')
    write_json(root/'diagnostic-authority.json', context)
    write_json(root/'config.json', context)
    write_json(root/'metrics.json', dict(runtime='SYNTHETIC_TEST_ONLY'))
    complete_diagnostic(root, reason='GOVERNANCE_REVIEW_PENDING', governance_status='PENDING')
    assert verify_diagnostic_completion(root)['status'] == 'DIAGNOSTIC_COMPLETE'
    with pytest.raises(ValueError, match='DIAGNOSTIC_ONLY'):
        seal_backtest(root)
    with pytest.raises(ValueError, match='DIAGNOSTIC_ONLY'):
        verify_backtest_seal(root)
    with pytest.raises(ValueError, match='DIAGNOSTIC_ONLY'):
        ModelRegistry(tmp_path/'registry').register(dict(historical_experiment=str(root)))
    release = build_diagnostic_release(root, tmp_path/'release')
    moved = tmp_path/'relocated'
    release.rename(moved)
    assert verify_diagnostic_release(moved)['promotion_eligible'] is False
    with pytest.raises(ValueError, match='DIAGNOSTIC_RELEASE'):
        verify_research_release(moved)
    (moved/'source-experiment/metrics.json').write_text('{}')
    with pytest.raises(ValueError, match='checksum'):
        verify_diagnostic_release(moved)
