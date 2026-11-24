"""Measure phase gates from retained reports without granting research decisions."""
from datetime import datetime, timezone
import json
import subprocess
from pathlib import Path

from quant.storage.research_store import digest_file, git_commit, write_json
from quant.research.data_interval import certify_data_interval


def report_phase(config, *, filing_coverage, share_coverage, discovery_gap, ceiling,
                 capital_verification, market_session_evidence):
    paths = dict(filing_coverage=Path(filing_coverage), share_coverage=Path(share_coverage),
        discovery_gap=Path(discovery_gap), ceiling=Path(ceiling), capital_verification=Path(capital_verification),
        market_session_evidence=Path(market_session_evidence))
    inputs = {k: json.loads(p.read_text(encoding='utf-8')) for k, p in paths.items()}
    interval = certify_data_interval(inputs['filing_coverage'], inputs['share_coverage'])
    write_json(config.data_dir/'reports/v2-data-interval.json', interval)
    from quant.research.evaluation_window import load_evaluation_window
    admitted = config.data_dir/'reports/v1-evaluation-window-admitted.json'
    from quant.governance.gates import GateRegistry
    gates = GateRegistry(config.data_dir).snapshot()
    admission, admission_error = gates['evaluation_window_admissible'], None
    if admitted.exists():
        try:
            load_evaluation_window(admitted)
            admission = gates['evaluation_window_admissible']
        except (ValueError, KeyError, OSError) as error:
            admission = False
            admission_error = str(error)
    rows = inputs['ceiling']['periods']
    best_overall = max(rows, key=lambda r: r['theoretical_max_coverage'], default={})
    def decisions(name):
        from quant.backtest.artifacts import verify_backtest_seal
        found = []
        for root in ('artifacts/backtests', 'research'):
            for p in sorted((config.data_dir/root).rglob(name)):
                try:
                    verify_backtest_seal(p.parent)
                    found.append(dict(path=str(p), sha256=digest_file(p), sealed=True,
                        decision=json.loads(p.read_text(encoding='utf-8')).get('decision')))
                except (ValueError, OSError, KeyError):
                    found.append(dict(path=str(p), sealed=False, decision='BLOCKED'))
        return found
    v1_decisions, v2_decisions = decisions('v1-decision.json'), decisions('v2-decision.json')
    cohorts = []
    from quant.forward.signal_store import read_signals
    for p in sorted((config.data_dir/'forward/registered').rglob('cohort.json')):
        batches, _ = read_signals(p.parent)
        if batches:
            cohorts.append(dict(path=str(p.parent), signal_sessions=len(batches)))
    from quant.research.coverage_policy import reliable_interval
    discovery_rows = [dict(r, thresholds_met=r['theoretical_max_coverage'] >= 85
        and r['theoretical_max_top100_coverage'] >= 95) for r in rows]
    report = dict(epic='quant-parallel-evidence-completion', governance=gates,
        assessed_at=datetime.now(timezone.utc).isoformat(), git_head_sha=git_commit(),
        working_tree_clean=not bool(subprocess.run(['git', 'status', '--porcelain'],
            capture_output=True, text=True, check=True).stdout.strip()),
        phase_status='IN_PROGRESS_EXTERNAL_EVIDENCE_REQUIRED',
        latest_certified_market_session=inputs['market_session_evidence'].get('latest_retained_certified_session'),
        market_session_evidence=dict(path=str(paths['market_session_evidence']), sha256=digest_file(paths['market_session_evidence']),
            scope='Retained prior-phase market certification; no claim of a newer market session'),
        filing_discovery=dict(missing_cells=inputs['discovery_gap']['missing_cells'],
            distinct_instruments=inputs['discovery_gap']['missing_instruments'],
            best_theoretical_overall=max((r['theoretical_max_coverage'] for r in rows), default=None),
            best_theoretical_top100=max((r['theoretical_max_top100_coverage'] for r in rows), default=None),
            top100_at_best_overall_cutoff=best_overall.get('theoretical_max_top100_coverage'),
            best_overall_cutoff=best_overall.get('as_of'),
            discovery_targets=dict(overall=85, top100=95),
            target_interval_available=reliable_interval(discovery_rows) is not None),
        capital_events=inputs['capital_verification'], shared_data_interval=interval,
        v1=dict(status='BLOCKED' if not admission else 'AWAITING_SEALED_MATCHED_BASELINES',
            outcome='BLOCKED_BY_GOVERNANCE' if not admission else 'INCONCLUSIVE',
            governance_status=gates['human_review_status'], PRICE='BLOCKED', TOTAL_RETURN='BLOCKED',
            human_window_admitted=admission, admission_error=admission_error, decisions=v1_decisions),
        v2=dict(status=v2_decisions[-1]['decision'] if v2_decisions else 'BLOCKED',
            reason='Certified shared data interval, human-approved frozen specification and sealed V1 prerequisites required',
            real_oos_evidence=any(r['sealed'] for r in v2_decisions), decisions=v2_decisions, value_required=True),
        forward=dict(state='COLLECTING' if cohorts else 'NOT_LAUNCHED', cohorts=cohorts,
            real_collection_blocked_by_governance=not admission,
            minimum_signal_sessions=126, minimum_rebalance_cycles=6,
            minimum_matured_63_session_signals=30, automatic_promotion=False),
        elastic_net=dict(status='GATED_NOT_FITTED', ensemble_weight=0,
            reason='Requires V2 GO_FURTHER_V2_RESEARCH and stable multi-year PIT coverage'),
        input_reports={k:dict(path=str(p), sha256=digest_file(p)) for k, p in paths.items()},
        production_publishing=False)
    write_json(config.data_dir/'reports/historical-forward-validation-phase.json', report)
    write_json(config.data_dir/'reports/parallel-evidence-completion-phase.json', report)
    return report


def main():
    from quant.pipeline.cli import parser_config
    parser, config = parser_config(__doc__)
    for name in ('filing-coverage', 'share-coverage', 'discovery-gap', 'ceiling', 'capital-verification', 'market-session-evidence'):
        parser.add_argument('--'+name, type=Path, required=True)
    args = parser.parse_args()
    report = report_phase(args.config(config), **{k: getattr(args, k) for k in
        ('filing_coverage', 'share_coverage', 'discovery_gap', 'ceiling', 'capital_verification', 'market_session_evidence')})
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
