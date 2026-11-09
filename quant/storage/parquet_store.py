"""One atomic daily partition inside year/month directories; reruns replace a day."""
from pathlib import Path
from io import BytesIO

import pandas as pd

from quant.data.http import atomic_write
from quant.data.nse_bhavcopy import validate_bars


def write_parquet(frame: pd.DataFrame, path: Path) -> Path:
    buffer = BytesIO()
    frame.to_parquet(buffer, index=False, compression='zstd')
    atomic_write(path, buffer.getvalue())
    return path


def write_prices(frame: pd.DataFrame, root: Path) -> list[Path]:
    validate_bars(frame)
    paths = []
    for day, group in frame.groupby('trade_date'):
        path = root / f'year={day.year}' / f'month={day.month:02d}' / f'{day:%Y-%m-%d}.parquet'
        paths.append(write_parquet(group, path))
    return paths
