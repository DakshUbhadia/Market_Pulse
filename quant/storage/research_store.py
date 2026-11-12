"""Reproducible research manifests and immutable run directories."""
import hashlib
import json
import math
import subprocess
from dataclasses import asdict, is_dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from quant.data.http import atomic_write
from quant.storage.duckdb_store import query_dataset, dataset_files


def clean_json(value):
    if is_dataclass(value):
        return clean_json(asdict(value))
    if isinstance(value, dict):
        return {str(key): clean_json(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [clean_json(item) for item in value]
    if isinstance(value, (float, np.floating)):
        return float(value) if math.isfinite(value) else None
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, np.bool_):
        return bool(value)
    if isinstance(value, (str, bool, int)) or value is None:
        return value
    return str(value)


def write_json(path, value):
    atomic_write(path, json.dumps(clean_json(value), indent=2, allow_nan=False).encode())


def digest_file(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024*1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def git_commit():
    from quant.config import REPO_ROOT
    result = subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=REPO_ROOT, capture_output=True, text=True, check=True)
    return result.stdout.strip()


def input_manifest(config, as_of):
    from quant.config import REPO_ROOT
    import importlib.metadata
    files = []
    for dataset in ('adjusted_prices', 'indices', 'delivery', 'corporate_actions'):
        for filename in dataset_files(config.data_dir, dataset):
            path = Path(filename)
            if dataset != 'corporate_actions' and path.stem > str(as_of)[:10]:
                continue
            files.append(dict(path=str(path.relative_to(config.data_dir)), bytes=path.stat().st_size,
                              sha256=digest_file(path)))
    for path in (config.calendar_path, config.data_dir/'normalized/security_history/identities.parquet'):
        if path.exists():
            files.append(dict(path=str(path.relative_to(config.data_dir)),
                              bytes=path.stat().st_size, sha256=digest_file(path)))
    encoded = json.dumps(files, sort_keys=True).encode()
    code_files = list((REPO_ROOT / 'quant').glob('*.py'))
    for name in ('data', 'features', 'models', 'pipeline', 'storage', 'universe', 'backtest'):
        code_files.extend(path for path in (REPO_ROOT / 'quant' / name).rglob('*.py') if 'tests' not in path.parts)
    code = {str(path.relative_to(REPO_ROOT)): digest_file(path) for path in sorted(set(code_files))}
    dependencies = {name: importlib.metadata.version(name) for name in ('pandas', 'numpy', 'duckdb', 'pyarrow')}
    return dict(as_of=str(as_of), git_commit=git_commit(), files=files, source_code_sha256=code, dependencies=dependencies,
                input_sha256=hashlib.sha256(encoded).hexdigest())


def verify_manifest(config, manifest):
    from quant.config import REPO_ROOT
    for item in manifest['files']:
        path = (config.data_dir / item['path']).resolve()
        if not path.is_relative_to(config.data_dir.resolve()) or digest_file(path) != item['sha256']:
            raise ValueError('Research inputs changed; rebuild features and the manifest')
    for filename, expected in manifest.get('source_code_sha256', {}).items():
        path = (REPO_ROOT / filename).resolve()
        if not path.is_relative_to(REPO_ROOT.resolve()) or digest_file(path) != expected:
            raise ValueError('Research source code changed; rebuild features and the manifest')


def load_research_data(config, as_of):
    from datetime import date
    from quant.pipeline.update_calendar import read_calendar
    calendar = read_calendar(config, date(2010, 1, 1), as_of)
    sessions = calendar.loc[calendar.is_trading_session, 'trade_date']
    # V1 only researches EQ bars. Project away raw archive metadata and unused
    # OHLC copies before materializing a sixteen-year frame in pandas.
    import duckdb
    with duckdb.connect(':memory:') as connection:
        relation = connection.sql('SELECT trade_date, instrument_id, symbol, series, adjusted_open, '
            'adjusted_close, raw_close, volume, traded_value, adjustment_status '
            'FROM read_parquet(?, hive_partitioning=false, union_by_name=true) '
            "WHERE series='EQ' AND trade_date <= ?", params=[dataset_files(config.data_dir, 'adjusted_prices'), as_of])
        table = relation.to_arrow_table() if hasattr(relation, 'to_arrow_table') else relation.arrow()
        if hasattr(table, 'read_all'):
            table = table.read_all()
        prices = table.to_pandas(categories=['instrument_id','symbol','series','adjustment_status'], split_blocks=True)
    indices = query_dataset(config.data_dir, 'indices', end=as_of)
    benchmark = indices[indices.index_name == 'NIFTY 500'].copy()
    try:
        delivery = query_dataset(config.data_dir, 'delivery', end=as_of)
    except FileNotFoundError:
        delivery = None
    return prices, benchmark, sessions, delivery, indices
