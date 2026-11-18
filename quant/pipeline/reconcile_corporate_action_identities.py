"""Reconcile stale API ISINs using dated observations; preserve prior normalized bytes."""
import json

import pandas as pd

from quant.data.http import atomic_write
from quant.data.nse_corporate_actions import action_identity_lookup, reconcile_action_identities
from quant.storage.parquet_store import read_parquet_file, write_parquet
from quant.storage.research_store import digest_file, write_json


def reconcile(config):
    history = read_parquet_file(config.data_dir/'normalized/security_history/identities.parquet')
    lookup = action_identity_lookup(history)
    changed, reviewed, files_changed, reconciled = [], 0, 0, set()
    for path in sorted((config.data_dir/'normalized/corporate_actions').rglob('*.parquet')):
        before = read_parquet_file(path)
        after = reconcile_action_identities(before,lookup=lookup)
        differs = before.instrument_id.fillna('').ne(after.instrument_id.fillna(''))
        reviewed += int(after.identity_resolution.eq('IDENTITY_TRANSITION_UNASSESSED').sum())
        reconciled.update(after.loc[after.identity_resolution.eq('STALE_SOURCE_ISIN_RECONCILED'),'event_id'])
        if not differs.any():
            continue
        digest = digest_file(path)
        archive = config.data_dir/'normalized/corporate_action_revisions'/f'{digest}.bin'
        if not archive.exists():
            atomic_write(archive,path.read_bytes())
        for i in after.index[differs]:
            changed.append(dict(event_id=after.loc[i,'event_id'],symbol=after.loc[i,'symbol'],
                ex_date=str(pd.Timestamp(after.loc[i,'ex_date']).date()),
                previous_instrument_id=before.loc[i,'instrument_id'],instrument_id=after.loc[i,'instrument_id'],
                resolution=after.loc[i,'identity_resolution'],previous_normalized_sha256=digest))
        write_parquet(after,path)
        files_changed += 1
    report = dict(status='REBUILD_REQUIRED' if changed else 'UNCHANGED',files_changed=files_changed,
        changed_records=len(changed),reconciled_records=len(reconciled),changes=changed,unassessed_transition_records=reviewed,
        method='SAME_ISIN_STEM_AND_UNIQUE_DATED_IDENTITY_STABLE_BEFORE_AND_ON_EVENT_DATE',current_master_used=False)
    write_json(config.data_dir/'reports/corporate-action-identity-reconciliation.json',report)
    return report


def main():
    from quant.pipeline.cli import parser_config
    parser,config = parser_config(__doc__)
    args = parser.parse_args()
    report = reconcile(args.config(config))
    print(json.dumps({key:value for key,value in report.items() if key != 'changes'},indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
