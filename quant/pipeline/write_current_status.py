"""Produce measured local status; missing evidence stays explicitly unknown."""
from datetime import datetime, timezone
import json
import subprocess
from pathlib import Path
from quant.storage.research_store import write_json, git_commit, digest_file
from quant import version


def read_report(path):
    if not path.exists():
        return dict(status='UNASSESSED',path=str(path))
    return dict(path=str(path),sha256=digest_file(path),report=json.loads(path.read_text(encoding='utf-8')))


def write_current_status(config, *, public_state=None, evidence_dir=None):
    from quant.identity.transitions import TRANSITION_VERSION
    from quant.pipeline.cli import completed_day
    root = config.data_dir
    evidence_root = Path(evidence_dir) if evidence_dir is not None else root
    def evidence(name):
        current = root/'reports'/name
        return read_report(current if current.exists() else evidence_root/'reports'/name)
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
        fundamental_acquisition_plan=read_report(root/'reports/fundamental-acquisition-plan.json'),
        evidence_closure_diagnostics=read_report(root/'reports/diagnostic-summary.json'),
        share_history_coverage=read_report(root/'reports/share-history-coverage.json'),
        fundamentals=read_report(root/'reports/fundamental-universe-coverage.json'),
        fundamental_backfill=read_report(root/'reports/fundamental-backfill-status.json'),
        fundamental_documents=read_report(root/'reports/fundamental-document-backfill-status.json'),
        historical_costs=read_report(root/'reports/historical-cost-evidence-review.json'),
        factor_v2_enabled=False,production_promotion=False)
    from quant.monitoring.incidents import IncidentLedger
    ledger = root/'research/incidents'
    report['incident_ledger'] = (IncidentLedger(ledger).report() if (ledger/'ledger.json').is_file()
                                 else dict(status='UNASSESSED', unresolved_incidents=None))
    report['registered_forward_cohorts'] = [str(p.parent.relative_to(root)) for p in
        sorted((root/'forward/registered').rglob('cohort.json')) if any((p.parent/'signals').glob('*.json'))]
    report['research_releases'] = [str(p.parent.relative_to(root)) for p in sorted((root/'research/releases').rglob('checksums.json'))]
    certificate = report['implementation_certification'].get('report', {})
    report.update(PUBLIC_MAIN_SHA=(public_state or {}).get('PUBLIC_MAIN_SHA') or certificate.get('PUBLIC_MAIN_SHA'),
        LOCAL_IMPLEMENTATION_SHA=git_commit(), RESEARCH_CERTIFIED_SHA=certificate.get('RESEARCH_CERTIFIED_SHA'))
    report['fundamental_coverage_ceiling'] = read_report(root/'reports/fundamental-coverage-ceiling.json')
    report['fundamental_discovery_expansion'] = read_report(root/'reports/fundamental-discovery-expansion.json')
    report['share_evidence_plan'] = read_report(root/'reports/share-evidence-plan.json')
    report['fundamental_discovery_gap'] = read_report(root/'reports/fundamental-discovery-gap.json')
    report['capital_event_ledger'] = read_report(root/'reports/capital-event-candidates.json')
    report['historical_certification_phase'] = read_report(root/'reports/historical-certification-phase.json')
    report['filing_coverage'] = evidence('fundamental-universe-coverage.json')
    report['share_coverage'] = evidence('share-history-coverage.json')
    report['v2_data_interval'] = evidence('v2-data-interval.json')
    report['tidewater_governance'] = evidence('security-transitions/tidewater-2016-human-review.json')
    report['evaluation_window_admission'] = evidence('v1-evaluation-window-admitted.json')
    report['historical_forward_validation_phase'] = evidence('historical-forward-validation-phase.json')
    report['evidence_source_root'] = str(evidence_root)
    report['working_tree_clean'] = not bool(subprocess.run(['git', 'status', '--porcelain'],
        capture_output=True, text=True, check=True).stdout.strip())
    report['certificate_applies_to_local_implementation'] = bool(report['working_tree_clean']
        and certificate.get('status') == 'CERTIFIED' and report['RESEARCH_CERTIFIED_SHA'] == git_commit())
    phase = report['historical_forward_validation_phase'].get('report', {})
    report['latest_certified_market_session'] = phase.get('latest_certified_market_session')
    report['latest_certified_market_session_provenance'] = phase.get('market_session_evidence')
    report['V1_BASELINE_STATE'] = phase.get('v1', dict(status='UNASSESSED', experiments=experiments))
    report['V2_STATE'] = phase.get('v2', dict(status='BLOCKED', reason='Certified interval and reviewed spec required'))
    report['forward_cohort_state'] = dict(registered_cohorts=report['registered_forward_cohorts'],
        state='COLLECTING' if report['registered_forward_cohorts'] else 'NOT_LAUNCHED')
    write_json(root/'reports/current-status.json',report)
    return report


def main():
    from quant.pipeline.cli import parser_config
    parser, config = parser_config(__doc__)
    parser.add_argument('--evidence-dir', type=Path)
    args = parser.parse_args()
    print(json.dumps(write_current_status(args.config(config), evidence_dir=args.evidence_dir),indent=2))


if __name__ == '__main__':
    main()
