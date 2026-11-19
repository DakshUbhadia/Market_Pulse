"""Materialize the authoritative missing name/month discovery workload."""
import argparse
import json
from pathlib import Path

import pandas as pd

from quant.data.fundamental_discovery_gap import build_discovery_gap
from quant.storage.parquet_store import read_parquet_file, write_parquet
from quant.storage.research_store import digest_file, write_json


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('universe', 'coverage', 'ceiling', 'filings', 'output'):
        parser.add_argument('--'+name, type=Path, required=True)
    args = parser.parse_args()
    report = build_discovery_gap(read_parquet_file(args.universe),
        json.loads(args.coverage.read_text(encoding='utf-8')),
        json.loads(args.ceiling.read_text(encoding='utf-8')), read_parquet_file(args.filings))
    report['input_sha256'] = {str(p): digest_file(p) for p in
                             (args.universe, args.coverage, args.ceiling, args.filings)}
    write_parquet(pd.DataFrame(report['cells']), args.output.with_suffix('.parquet'))
    write_json(args.output, report)
    print(json.dumps({k: v for k, v in report.items() if k != 'cells'}, indent=2))


if __name__ == '__main__':
    main()
