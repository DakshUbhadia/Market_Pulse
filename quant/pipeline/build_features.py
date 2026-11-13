"""Build a research snapshot only after independent readiness checks pass."""
import argparse
from datetime import date
from pathlib import Path
from dataclasses import replace

from quant.config import Config
from quant.features.matrix import build_feature_matrix
from quant.pipeline.check_research_ready import require_research_ready
from quant.storage.research_store import load_research_data, input_manifest, write_json, digest_file
from quant.storage.parquet_store import write_parquet
from quant.universe.config import UniverseConfig
from quant.version import FEATURE_VERSION
from quant.data.http import atomic_write


def build_features(config, as_of):
    require_research_ready(config, as_of)
    prices, benchmark, sessions, delivery, _ = load_research_data(config, as_of)
    universe = UniverseConfig()
    frame = build_feature_matrix(prices, benchmark, sessions, delivery=delivery, as_of=as_of, universe_config=universe)
    target = config.data_dir / 'features/factor_v1' / f'year={as_of.year}' / f'{as_of}.parquet'
    if target.exists():
        previous = target.parent / 'revisions' / f'{as_of}-{digest_file(target)}'
        for source in (target, target.with_suffix('.manifest.json')):
            if source.exists():
                archived = previous / source.name
                if not archived.exists():
                    atomic_write(archived, source.read_bytes())
    write_parquet(frame, target)
    write_parquet(frame[['as_of', 'instrument_id', 'symbol', 'series', 'eligible', 'history_sessions',
                         'trading_presence_252', 'adv60', 'exclusion_reason']],
                  config.data_dir / 'normalized/universe' / f'year={as_of.year}' / f'{as_of}.parquet')
    manifest = input_manifest(config, as_of)
    manifest.update(feature_version=FEATURE_VERSION, universe_settings=vars(universe), feature_sha256=digest_file(target))
    write_json(target.with_suffix('.manifest.json'), manifest)
    return frame, target


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--as-of', type=date.fromisoformat, required=True)
    parser.add_argument('--data-dir', type=Path)
    args = parser.parse_args()
    config = Config()
    if args.data_dir:
        config = replace(config, data_dir=args.data_dir)
    try:
        frame, target = build_features(config, args.as_of)
    except (OSError, ValueError) as error:
        print(f'Feature build blocked: {error}')
        return 1
    print(f'{len(frame)} feature rows: {target}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
