"""Local research rankings, with inspectable inputs; never public buy recommendations."""
import argparse
import json
from datetime import date
from pathlib import Path
from dataclasses import replace

import pandas as pd

from quant.config import Config
from quant.data.http import atomic_write
from quant.pipeline.check_research_ready import require_research_ready
from quant.models.factor_v1 import score_factor_v1
from quant.storage.parquet_store import write_parquet
from quant.storage.research_store import verify_manifest, write_json, digest_file
from quant.version import MODEL_VERSION


def run_factor_v1(config, as_of):
    require_research_ready(config, as_of)
    feature_path = config.data_dir / 'features/factor_v1' / f'year={as_of.year}' / f'{as_of}.parquet'
    manifest = json.loads(feature_path.with_suffix('.manifest.json').read_text())
    verify_manifest(config, manifest)
    if digest_file(feature_path) != manifest['feature_sha256']:
        raise ValueError('Feature artifact checksum differs from its manifest')
    result = score_factor_v1(pd.read_parquet(feature_path))
    if result.empty:
        raise ValueError('No stocks have complete point-in-time V1 features')
    root = config.data_dir / 'artifacts/factor_v1'
    path = root / f'{as_of}.parquet'
    if path.exists():
        revision = root / 'revisions' / f'{as_of}-{digest_file(path)}'
        for source in (path, path.with_suffix('.csv'), path.with_suffix('.json'), root/f'{as_of}-top30-review.txt'):
            if source.exists() and not (revision/source.name).exists():
                atomic_write(revision/source.name, source.read_bytes())
    write_parquet(result, path)
    atomic_write(path.with_suffix('.csv'), result.to_csv(index=False).encode())
    write_json(path.with_suffix('.json'), dict(model_version=MODEL_VERSION, feature_manifest=manifest,
                                               recommendation=False, score_interpretation='PERCENTILE_NOT_PROBABILITY'))
    top = result.head(30)[['rank', 'symbol', 'percentile_score', 'raw_score', 'vol_63', 'adv_60']]
    atomic_write(root / f'{as_of}-top30-review.txt', ('RESEARCH ONLY: percentile rankings, not profit probabilities.\n'
                                                    + top.to_string(index=False)).encode())
    return result, path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--as-of', type=date.fromisoformat, required=True)
    parser.add_argument('--data-dir', type=Path)
    args = parser.parse_args()
    config = replace(Config(), data_dir=args.data_dir) if args.data_dir else Config()
    try:
        rows, path = run_factor_v1(config, args.as_of)
    except (OSError, ValueError) as error:
        print(f'Ranking blocked: {error}')
        return 1
    print(rows.head(30)[['rank', 'symbol', 'percentile_score']].to_string(index=False))
    print(path)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
