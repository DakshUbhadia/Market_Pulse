"""Produce measured local status; missing evidence stays explicitly unknown."""
from datetime import datetime, timezone
import json
from quant.storage.research_store import write_json, git_commit, digest_file
from quant import version


def read_report(path):
    if not path.exists():
        return dict(status='UNASSESSED',path=str(path))
    return dict(path=str(path),sha256=digest_file(path),report=json.loads(path.read_text(encoding='utf-8')))


def write_current_status(config, *, public_state=None):
    from quant.identity.transitions import TRANSITION_VERSION
    from quant.pipeline.cli import completed_day
    root = config.data_dir
    experiments = []
    for path in sorted((root/'research/experiments').rglob('outcome.json')):
        experiments.append(read_report(path))
    report = dict(generated_at=datetime.now(timezone.utc).isoformat(),local_commit=git_commit(),
        public_state=public_state or dict(status='UNVERIFIED',reason='No fresh GitHub response supplied'),
        working_tree_evidence='Local code may differ from local_commit; CI must match committed source',
        versions={name:getattr(version,name) for name in dir(version) if name.endswith('_VERSION')},
        security_transition_version=TRANSITION_VERSION,completed_eod_cutoff=str(completed_day(config)),
        latest_certified_session=read_report(root/'reports/research-readiness.json'),
        blocker=read_report(root/'reports/security-transitions/tidewater-2016.json'),
        baseline_experiments=experiments,
        forward_cohorts=[p.name for p in (root/'forward/factor_v1/cohorts').glob('*') if p.is_dir() and any((p/'signals').glob('*.json'))],
        parser_stability=read_report(root/'reports/fundamental-parser-stability.json'),
        source_health=read_report(root/'reports/source-health.json'),
        implementation_certification=read_report(root/'reports/implementation-certification.json'),
        fundamental_acquisition=read_report(root/'reports/fundamental-acquisition.json'),
        share_history_coverage=read_report(root/'reports/share-history-coverage.json'),
        fundamentals=read_report(root/'reports/fundamental-universe-coverage.json'),
        fundamental_backfill=read_report(root/'reports/fundamental-backfill-status.json'),
        fundamental_documents=read_report(root/'reports/fundamental-document-backfill-status.json'),
        historical_costs=read_report(root/'reports/historical-cost-evidence-review.json'),
        factor_v2_enabled=False,production_promotion=False)
    write_json(root/'reports/current-status.json',report)
    return report


def main():
    from quant.pipeline.cli import parser_config
    parser, config = parser_config(__doc__)
    args = parser.parse_args()
    print(json.dumps(write_current_status(args.config(config)),indent=2))


if __name__ == '__main__':
    main()
