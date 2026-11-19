"""Build historical shares from archived equity anchors and dated capital events."""
import json
from pathlib import Path

import pandas as pd

from quant.features.share_history import derive_share_anchors, share_history
from quant.pipeline.audit_share_history_coverage import verify_share_archives
from quant.storage.parquet_store import read_parquet_file, write_parquet
from quant.storage.research_store import digest_file, write_json


def main():
    from quant.pipeline.cli import parser_config
    parser, config = parser_config(__doc__)
    for name in ('keys', 'capital-events', 'share-coverage', 'output'):
        parser.add_argument('--'+name, type=Path, required=True)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument('--anchors', type=Path)
    source.add_argument('--filings', type=Path, help='Parsed normalized paid_up_capital / face_value facts')
    args = parser.parse_args()
    config = args.config(config)
    anchors = read_parquet_file(args.anchors) if args.anchors else derive_share_anchors(read_parquet_file(args.filings))
    frames = [verify_share_archives(f, config.data_dir) for f in
              (anchors, read_parquet_file(args.capital_events), read_parquet_file(args.share_coverage))]
    keys = read_parquet_file(args.keys)
    keys = keys[pd.to_datetime(keys.as_of).between(pd.Timestamp(args.start), pd.Timestamp(args.end))]
    if 'signal_timestamp' not in keys:
        keys = keys.assign(signal_timestamp=pd.to_datetime(keys.as_of).dt.tz_localize('Asia/Kolkata')+pd.Timedelta(hours=15, minutes=30))
    if keys.duplicated(['as_of', 'instrument_id']).any():
        raise ValueError('Historical share keys must be unique per date and instrument')
    result = share_history(*frames, keys)
    write_parquet(result, args.output)
    paths = (args.keys, args.anchors or args.filings, args.capital_events, args.share_coverage)
    report = dict(rows=len(result), verified_rows=int(result.value_feature_valid.sum()) if len(result) else 0,
        current_shares_backfilled=False, input_sha256={str(p): digest_file(p) for p in paths},
        output_sha256=digest_file(args.output))
    write_json(args.output.with_suffix('.json'), report)
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
