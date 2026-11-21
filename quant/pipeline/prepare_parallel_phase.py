"""Record intentional PENDING governance and copy only checksum-bound review inputs."""
import json
from pathlib import Path
import shutil

from quant.config import REPO_ROOT
from quant.forward.signal_store import append_record
from quant.governance.gates import GateRegistry, GATE_ID, SUBJECT_ID, default_gate
from quant.governance.review import record_pending_review
from quant.research.evaluation_window import load_evaluation_window
from quant.storage.research_store import write_json, digest_file


def prepare_parallel_phase(config, *, review_evidence_root):
    root = config.data_dir
    original = REPO_ROOT/'quant/artifacts/historical-forward-validation/reports/v1-evaluation-declaration.json'
    declaration = load_evaluation_window(original, require_admission=False)
    target = root/'reports/v1-evaluation-declaration.json'
    append_record(target, declaration)
    original_base = Path(review_evidence_root).resolve()
    copied = {}
    for event in declaration['blocking_events']:
        for name, expected in event['evidence_hashes'].items():
            source = (original_base/name).resolve()
            destination = (root/name).resolve()
            if (not source.is_relative_to(original_base) or not destination.is_relative_to(root.resolve())
                    or not source.is_file() or source.is_symlink() or digest_file(source) != expected):
                raise ValueError('Prepared diagnostic review evidence is absent or changed')
            destination.parent.mkdir(parents=True, exist_ok=True)
            if destination.exists() and digest_file(destination) != expected:
                raise ValueError('Existing review evidence must not be overwritten')
            if not destination.exists():
                shutil.copyfile(source, destination)
            copied[name] = expected
    gates = GateRegistry(root).initialize()
    if gates['human_review_status'] != 'PENDING':
        raise ValueError('This phase initializer cannot replace an existing human decision')
    gate = default_gate()
    record_pending_review(review_type='TRANSITION_EXHAUSTION', subject_id=SUBJECT_ID,
        subject_sha256=gate['subject_sha256'], automated_packet=gate['evidence_artifact'],
        output=root/'reports/security-transitions/tidewater-2016-human-review-pending.json')
    write_json(root/'reports/governance-gates.json', gates)
    write_json(root/'reports/governance-dependencies.json', gates['dependencies'])
    report = dict(epic='quant-parallel-evidence-completion', governance_gate=GATE_ID,
        human_review_status='PENDING', fallback_window='PREPARED_BUT_NOT_ADMITTED',
        V1_PRICE='BLOCKED_BY_GOVERNANCE', V1_TOTAL_RETURN='BLOCKED_BY_GOVERNANCE',
        real_forward_cohorts='BLOCKED_BY_GOVERNANCE', production_publishing='BLOCKED_BY_GOVERNANCE',
        diagnostic_replay_allowed=True, copied_review_evidence=copied,
        real_human_approval_created=False, source_market_corpus_read_only=True)
    write_json(root/'reports/parallel-evidence-initialization.json', report)
    return report


def main():
    from quant.pipeline.cli import parser_config
    parser, config = parser_config(__doc__)
    parser.add_argument('--review-evidence-root', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(prepare_parallel_phase(args.config(config), review_evidence_root=args.review_evidence_root), indent=2))


if __name__ == '__main__':
    main()
