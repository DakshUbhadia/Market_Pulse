"""Cross-platform regressions for the storage behavior used by Linux CI."""
import os
from pathlib import Path

import pandas as pd
import pyarrow.dataset as ds
import pytest


@pytest.fixture
def hive_partition_reads(monkeypatch):
    """Exercise POSIX-style Hive inference even on Windows developer machines."""
    original = pd.read_parquet

    def read(path, *args, **kwargs):
        if isinstance(path, (str, os.PathLike)) and any('=' in part for part in Path(path).parts):
            return ds.dataset([Path(path).resolve().as_posix()], format='parquet',
                partitioning=ds.HivePartitioning.discover(infer_dictionary=True)).to_table(
                    columns=kwargs.get('columns')).to_pandas()
        return original(path, *args, **kwargs)

    monkeypatch.setattr(pd, 'read_parquet', read)
