"""Explicit governance states and dependencies, independent of data acquisition.

The packaged pending decision is the default, even without a local journal.
Only a matching immutable human review can replace it with approval/rejection.
"""
from datetime import datetime, timezone
import json
from pathlib import Path

from quant.config import REPO_ROOT
from quant.forward.signal_store import append_record, content_hash
from quant.governance.review import require_review
from quant.storage.research_store import digest_file

GATE_ID = 'TIDEWATER_2016_HUMAN_REVIEW'
SUBJECT_ID = 'TIDEWATER_2016'
WINDOW_GATE_ID = 'V1_EVALUATION_WINDOW_ADMISSION'
STATES = {'NOT_REQUIRED', 'PENDING', 'APPROVED', 'REJECTED', 'SUPERSEDED'}
DEPENDENCIES = {
    'V1_HISTORICAL_SEAL': [GATE_ID, WINDOW_GATE_ID],
    'V1_MODEL_REGISTRATION': ['V1_HISTORICAL_SEAL'],
    'V1_REAL_FORWARD': ['V1_MODEL_REGISTRATION'],
    'V2_SPEC_FREEZE': ['V1_HISTORICAL_SEAL'],
    'V2_PROMOTION': ['V1_HISTORICAL_SEAL'],
    'V2_REAL_FORWARD': ['V2_PROMOTION'],
    'PRODUCTION_PUBLISHING': ['V1_REAL_FORWARD'],
    'FILING_DISCOVERY': [], 'CAPITAL_EVENT_VERIFICATION': [], 'SHARE_CHAINS': [],
    'V2_DATA_MATRIX': [], 'DIAGNOSTIC_V1': [], 'DIAGNOSTIC_V2': [],
    'DIAGNOSTIC_RELEASE': [], 'TEST_FORWARD': [], 'MONITORING_DRY_RUN': [],
}
ALIASES = {'V1_SEAL': 'V1_HISTORICAL_SEAL', 'V1_FORWARD': 'V1_REAL_FORWARD'}


class GovernanceBlocked(ValueError):
    outcome = 'BLOCKED_BY_GOVERNANCE'

    def __init__(self, action, gate):
        self.action, self.gate = action, gate
        super().__init__(f'{action} blocked by {gate["gate_id"]}: {gate["status"]} ({gate["blocking_reason"]})')

    def metadata(self):
        return dict(status='BLOCKED', outcome=self.outcome, governance_gate=self.gate['gate_id'],
                    governance_status=self.gate['status'], reason=str(self))


def data_root_for(path):
    path = Path(path).resolve()
    for parent in (path, *path.parents):
        if parent.name in ('research', 'artifacts', 'forward'):
            return parent.parent
    return path.parent


def default_gate():
    packet = REPO_ROOT/'quant/artifacts/historical-forward-validation/reports/security-transitions/tidewater-2016-human-review-packet.json'
    body = json.loads(packet.read_text(encoding='utf-8'))
    return dict(gate_id=GATE_ID, gate_type='TRANSITION_EXHAUSTION', subject_id=SUBJECT_ID,
        status='PENDING', required_for=['V1_SEAL', 'V1_MODEL_REGISTRATION', 'V1_FORWARD',
            'V2_SPEC_FREEZE', 'V2_PROMOTION', 'V2_REAL_FORWARD', 'PRODUCTION_PUBLISHING'],
        blocking_reason='HUMAN_REVIEW_PENDING',
        evidence_artifact=packet.relative_to(REPO_ROOT).as_posix(), evidence_sha256=digest_file(packet),
        subject_sha256=body['canonical_automated_audit_sha256'], review_artifact=None,
        created_at='2026-11-21T00:00:00+00:00', updated_at='2026-11-21T00:00:00+00:00',
        decision_source='USER_INSTRUCTION_LEAVE_HUMAN_REVIEW_PENDING')


def verify_gate(gate):
    original = default_gate()
    for field in ('gate_id', 'gate_type', 'subject_id', 'evidence_artifact', 'evidence_sha256', 'subject_sha256'):
        if gate.get(field) != original[field]:
            raise ValueError('Governance gate subject or evidence packet changed')
    if gate.get('status') not in STATES or gate['status'] == 'NOT_REQUIRED':
        raise ValueError('TIDEWATER human review is required')
    if gate['status'] in ('APPROVED', 'REJECTED'):
        decision = 'CONFIRM_EVIDENCE_EXHAUSTED_UNRESOLVED' if gate['status'] == 'APPROVED' else 'REOPEN_SEARCH'
        require_review(gate.get('review'), review_type='TRANSITION_EXHAUSTION', subject_id=SUBJECT_ID,
            subject_sha256=gate['subject_sha256'], decision=decision)
        review_path = Path(gate.get('review_artifact') or '')
        if not review_path.is_file() or digest_file(review_path) != gate.get('review_sha256'):
            raise ValueError('Governance human review artifact is missing or changed')
    elif gate.get('review') is not None or gate.get('review_artifact') is not None:
        raise ValueError('An undecided gate cannot carry an approval')
    return gate


class GateRegistry:
    def __init__(self, data_dir=None):
        self.root = Path(data_dir)/'research/governance' if data_dir is not None else None

    def snapshot(self):
        gate, previous = default_gate(), None
        paths = sorted((self.root/'events').glob('*.json')) if self.root else []
        for index, path in enumerate(paths):
            row = json.loads(path.read_text(encoding='utf-8'))
            if (row.get('sequence') != index or row.get('previous_sha256') != previous
                    or row.get('sha256') != content_hash({k: v for k, v in row.items() if k != 'sha256'})):
                raise ValueError('Governance journal changed')
            gate = verify_gate(row['gate'])
            previous = row['sha256']
        window_gate = dict(gate_id=WINDOW_GATE_ID, gate_type='EVALUATION_WINDOW_ADMISSION',
            subject_id='V1_FALLBACK_2017_03_28', status='PENDING', required_for=['V1_SEAL', 'V2_SPEC_FREEZE'],
            blocking_reason='EVALUATION_WINDOW_ADMISSION_PENDING',
            evidence_artifact='quant/artifacts/historical-forward-validation/reports/v1-evaluation-declaration.json',
            review_artifact=None, created_at=gate['created_at'], updated_at=gate['updated_at'])
        admitted = self.root.parent.parent/'reports/v1-evaluation-window-admitted.json' if self.root else None
        if gate['status'] == 'REJECTED':
            window_gate.update(status='REJECTED', blocking_reason='HUMAN_REVIEW_REJECTED')
        elif gate['status'] == 'APPROVED' and admitted is not None and admitted.is_file():
            try:
                from quant.research.evaluation_window import load_evaluation_window, window_subject
                window = load_evaluation_window(admitted)
                declaration = json.loads((REPO_ROOT/window_gate['evidence_artifact']).read_text(encoding='utf-8'))
                review = window['governance']['transition_reviews']['TIDEWATER-2016-03-17']
                if window_subject(window) != window_subject(declaration) or review != gate['review']:
                    raise ValueError('Admission does not bind the prepared declaration and current human review')
                window_gate.update(status='APPROVED', blocking_reason=None, review_artifact=str(admitted),
                    review_sha256=digest_file(admitted))
            except (ValueError, KeyError, OSError) as error:
                window_gate['blocking_reason'] = 'INVALID_ADMISSION_EVIDENCE: '+str(error)
        return dict(gates={GATE_ID: verify_gate(gate), WINDOW_GATE_ID: window_gate}, dependencies=DEPENDENCIES,
            human_review_status=gate['status'], evaluation_window_admissible=window_gate['status'] == 'APPROVED',
            fallback_window_state='ADMITTED' if window_gate['status'] == 'APPROVED' else 'PREPARED_BUT_NOT_ADMITTED')

    def _append(self, gate):
        if self.root is None:
            raise ValueError('A data directory is required to record a governance action')
        from quant.pipeline.state import state_lock
        with state_lock(self.root/'gates.lock'):
            self.snapshot()
            paths = sorted((self.root/'events').glob('*.json'))
            previous = json.loads(paths[-1].read_text(encoding='utf-8'))['sha256'] if paths else None
            body = dict(sequence=len(paths), previous_sha256=previous, gate=verify_gate(gate))
            append_record(self.root/'events'/f'{len(paths):08d}.json', dict(body, sha256=content_hash(body)))
        return gate

    def initialize(self):
        if self.root and list((self.root/'events').glob('*.json')):
            return self.snapshot()
        self._append(default_gate())
        return self.snapshot()

    def decide(self, review_path):
        review_path = Path(review_path)
        review = json.loads(review_path.read_text(encoding='utf-8'))
        gate = dict(self.snapshot()['gates'][GATE_ID], status=review.get('status'),
            review=review, review_artifact=str(review_path), review_sha256=digest_file(review_path),
            updated_at=datetime.now(timezone.utc).isoformat(),
            blocking_reason=None if review.get('status') == 'APPROVED' else 'HUMAN_REVIEW_REJECTED')
        return self._append(gate)

    def require(self, action):
        action = ALIASES.get(action, action)
        if action not in DEPENDENCIES:
            raise ValueError('Unknown governed action')
        snapshot = self.snapshot()
        def visit(name, ancestors):
            if name in ancestors:
                raise ValueError('Governance dependency cycle')
            if name in snapshot['gates']:
                gate = snapshot['gates'][name]
                if gate['status'] != 'APPROVED':
                    raise GovernanceBlocked(action, gate)
            else:
                for parent in DEPENDENCIES[name]:
                    visit(parent, ancestors | {name})
        visit(action, set())
        return snapshot


def require_action(config, action):
    return GateRegistry(config.data_dir).require(action)


def main():
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data-dir', type=Path, required=True)
    parser.add_argument('--review', type=Path, help='Completed immutable human review; omitted to record PENDING')
    args = parser.parse_args()
    registry = GateRegistry(args.data_dir)
    if args.review:
        registry.decide(args.review)
    print(json.dumps(registry.initialize(), indent=2))


if __name__ == '__main__':
    main()
