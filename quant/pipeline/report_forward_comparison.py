"""Compare registered cohorts on identical signal dates and portfolio assumptions."""
from pathlib import Path
import json
from quant.forward.signal_store import read_signals, content_hash
from quant.pipeline.report_forward_cohort import report_forward_cohort
from quant.storage.research_store import write_json


def shared_snapshot(root, batch):
    hashes = {r['source_manifest_hash'] for r in batch['signals']}
    if len(hashes) != 1:
        raise ValueError('Forward batch must share one source snapshot')
    digest = next(iter(hashes))
    manifest = json.loads((Path(root)/'sources'/f'{digest}.json').read_text(encoding='utf-8'))
    if content_hash(manifest) != digest:
        raise ValueError('Forward source manifest checksum changed')
    return dict(files=manifest['files'], input_sha256=manifest['input_sha256'],
                as_of=manifest['as_of'], execution_timestamp=batch['next_session_open'])


def report_forward_comparison(config, roots, *, as_of, output, incident_root=None):
    reports, dates, assumptions, snapshots = {}, None, None, None
    comparison_type = None
    for name, root in roots.items():
        batches, signals = read_signals(root)
        batches = [b for b in batches if b['as_of'] <= str(as_of)]
        if not batches:
            raise ValueError('A real forward cohort is required for every comparison arm')
        kinds = {b.get('cohort_type', 'REAL') for b in batches}
        if len(kinds) != 1 or (comparison_type is not None and comparison_type not in kinds):
            raise ValueError('TEST_ONLY cohorts cannot be compared with real forward evidence')
        comparison_type = next(iter(kinds))
        observed = [b['as_of'] for b in batches]
        policies = [{k: b['settings'][k] for k in ('portfolio', 'costs', 'return_basis', 'security_transition_version', 'lifecycle_scenario')}
                    for b in batches]
        if any(p != policies[0] for p in policies) or (dates is not None and (observed != dates or policies[0] != assumptions)):
            raise ValueError('Forward comparison requires identical dates and comparable execution assumptions')
        dates, assumptions = observed, policies[0]
        shared = [shared_snapshot(root, batch) for batch in batches]
        if snapshots is not None and shared != snapshots:
            raise ValueError('Matched forward cohorts require identical market/event snapshots and execution timestamps')
        snapshots = shared
        reports[name] = report_forward_cohort(config, as_of, root=Path(root), incident_root=incident_root)
    if len(reports) < 2:
        raise ValueError('Champion/challenger comparison requires at least two real cohorts')
    report = dict(as_of=str(as_of), reports=reports, matched_signal_dates=dates, assumptions=assumptions,
        cohort_type=comparison_type, real_forward_evidence=comparison_type == 'REAL', promotion_eligible=False,
        matched_snapshot_sha256=content_hash(snapshots),
        automatic_promotion=False, historical_backfill=False)
    write_json(output, report)
    return report


def main():
    from quant.pipeline.cli import parser_config
    parser, config = parser_config(__doc__)
    parser.add_argument('--v1-root', type=Path, required=True)
    parser.add_argument('--v2-root', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--incident-root', type=Path)
    args = parser.parse_args()
    print(json.dumps(report_forward_comparison(args.config(config), {'v1': args.v1_root, 'v2': args.v2_root},
        as_of=args.end, output=args.output, incident_root=args.incident_root), indent=2))


if __name__ == '__main__':
    main()
