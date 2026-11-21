"""Normalize archived capital events; never infer complete event coverage."""
import json
from pathlib import Path

from quant.data.capital_events import capital_event_ledger, capital_candidates_from_actions, EVENT_TYPES
from quant.pipeline.audit_share_history_coverage import verify_share_archives
from quant.storage.parquet_store import read_parquet_file, write_parquet
from quant.storage.research_store import digest_file, write_json


def main():
    from quant.pipeline.cli import parser_config
    parser, config = parser_config(__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument('--events', type=Path)
    source.add_argument('--corporate-actions-root', type=Path, help='Read-only retained official corpus')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    inputs = [args.events] if args.events else []
    if args.events:
        events = read_parquet_file(args.events)
    else:
        import pandas as pd
        from quant.data.http import atomic_write
        from quant.storage.duckdb_store import dataset_files
        inputs = dataset_files(args.corporate_actions_root, 'corporate_actions')
        actions = pd.concat([read_parquet_file(p) for p in inputs], ignore_index=True) if inputs else pd.DataFrame()
        events = capital_candidates_from_actions(actions)
        # Resolve raw evidence by its content hash; metadata sidecars are only
        # an index. Verify the actual byte before copying into this workspace.
        wanted = set(events.source_sha256.dropna()) if len(events) else set()
        archived = {}
        for path in (args.corporate_actions_root/'raw/nse/corporate_actions').rglob('*.json'):
            if not wanted:
                break
            digest = digest_file(path)
            if digest in wanted:
                dest = args.config(config).data_dir/'raw/capital-event-sources'/(digest+'.json')
                atomic_write(dest, path.read_bytes())
                archived[digest] = str(dest.relative_to(args.config(config).data_dir))
                wanted.remove(digest)
        if len(events):
            events['raw_path'] = events.source_sha256.map(archived)
    ledger = capital_event_ledger(events)
    ledger = verify_share_archives(ledger, args.config(config).data_dir)
    write_parquet(ledger, args.output)
    report = dict(status='POPULATED' if len(ledger) else 'NO_CAPITAL_EVENT_EVIDENCE', rows=len(ledger),
        verified_events=int(ledger.verification_status.eq('VERIFIED_COMPLETE').sum()), event_types=EVENT_TYPES,
        input_sha256={str(p): digest_file(p) for p in inputs}, output_sha256=digest_file(args.output),
        complete_chains_certified=False)
    write_json(args.output.with_suffix('.json'), report)
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
