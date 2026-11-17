"""One atomic daily partition inside year/month directories; reruns replace a day."""
from pathlib import Path
from io import BytesIO

import pandas as pd

from quant.data.http import atomic_write
from quant.data.nse_bhavcopy import validate_bars


def read_parquet_file(path: Path, *, columns=None) -> pd.DataFrame:
    """Read one physical file without inferring Hive columns from its parents.

    Passing a path to PyArrow can add year/month dictionary columns on POSIX.
    Rewriting that frame can persist those virtual fields and break later reads.
    A file handle makes file schema and column projection identical across OSes.
    """
    with Path(path).open('rb') as stream:
        return pd.read_parquet(stream, engine='pyarrow', columns=columns)


def write_parquet(frame: pd.DataFrame, path: Path, *, row_group_size=None) -> Path:
    buffer = BytesIO()
    options = {'row_group_size': row_group_size} if row_group_size is not None else {}
    frame.to_parquet(buffer, index=False, compression='zstd', **options)
    atomic_write(path, buffer.getvalue())
    return path


def write_prices(frame: pd.DataFrame, root: Path) -> list[Path]:
    validate_bars(frame)
    paths = []
    for day, group in frame.groupby('trade_date'):
        path = root / f'year={day.year}' / f'month={day.month:02d}' / f'{day:%Y-%m-%d}.parquet'
        paths.append(write_parquet(group, path))
    return paths
