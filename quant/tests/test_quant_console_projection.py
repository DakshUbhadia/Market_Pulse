import hashlib
import json

import pytest

from quant.pipeline.export_quant_status import publish_local, sign_status
from quant.pipeline.quant_console_projection import project_details


def write(root, name, value):
    path = root / 'reports' / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding='utf-8')


def test_console_projects_only_structural_evidence(tmp_path):
    current = {'registered_forward_cohorts': [], 'versions': {}}
    status = {'asOf': '2026-11-24T19:15:31.851Z', 'coverage': [], 'authority': 'STATUS_ONLY'}
    write(tmp_path, 'acceptance.json', {'recorded_at': '2026-11-24T19:15:39.569644+00:00',
        'software': {'unit_tests': 469, 'unit_failures': 0}, 'live_sources': {'passed': 6, 'failed': 5}})
    write(tmp_path, 'test-forward-dry-run.json', {'cohort_type': 'TEST_ONLY', 'real_forward_evidence': False,
        'promotion_eligible': False, 'as_of': '2025-02-17', 'signal_sessions': 4,
        'shadow_sessions': 78, 'outcomes': {'63': {'matured_outcomes': 1, 'mean_return': 'HIDDEN'}}})
    write(tmp_path, 'security-transitions/cairn-2017-evidence-gap.json',
        {'subject_id': 'CAIRN_2017', 'observed_block_date': '2017-04-26', 'source_records': ['HIDDEN']})
    write(tmp_path, 'diagnostic-v1-summary.json', {'attempts': [{'research_authority': 'DIAGNOSTIC_ONLY',
        'outcome': 'BLOCKED_BY_DATA', 'return_basis': 'PRICE', 'experiment_id': '20261122T091230-7b3bddc4',
        'reason': 'HIDDEN', 'scores': ['HIDDEN']}]})
    (tmp_path / 'reports' / 'capital-events-reviewed.json').write_text('{truncated', encoding='utf-8')

    kwargs = dict(reports=tmp_path / 'reports', archive=tmp_path, history=tmp_path, current_sha256='a' * 64)
    result = project_details(current, status, **kwargs)
    assert result == project_details(current, status, **kwargs)
    assert result['metrics']['localTestsPassed']['value'] == 469
    assert result['artifacts']['acceptance']['evidenceClass'] == 'LOCAL_TEST'
    assert result['metrics']['livePassed']['value'] == 6
    assert result['metrics']['liveFailed']['value'] == 5
    assert result['metrics']['realCohorts']['value'] == 0
    assert result['metrics']['testSignals']['value'] == 4
    assert result['metrics']['matured63']['value'] == 1
    assert result['cairnObserved'] == '2017-04-26'
    assert result['runs'][0]['id'] == '20261122T091230-7b3bddc4'
    assert 'HIDDEN' not in json.dumps(result)
    assert 'capital' not in result['artifacts']
    path = tmp_path / 'reports' / 'diagnostic-v1-summary.json'
    assert result['artifacts']['runs']['sha256'] == hashlib.sha256(path.read_bytes()).hexdigest()
    assert result['certifiedSha'] is None


def test_local_status_publication_is_idempotent_and_resists_rollbacks(tmp_path):
    output = tmp_path / 'quant.json'
    initial = dict(schemaVersion=2, runId='a' * 64, asOf='2026-11-24T19:15:31.851Z')
    later = dict(initial, runId='b' * 64, asOf='2026-11-24T19:16:31.851Z')
    initial_bytes = sign_status(initial, 'b' * 64)
    later_bytes = sign_status(later, 'b' * 64)
    publish_local(output, initial_bytes, initial)
    publish_local(output, later_bytes, later)
    with pytest.raises(ValueError, match='older'):
        publish_local(output, initial_bytes, initial)
    output.write_bytes(b'{interrupted')
    publish_local(output, later_bytes, later)
    assert output.read_bytes() == later_bytes
    assert len(list((tmp_path / 'quant.json.history').glob('*.json'))) == 2
