"""Read local price partitions with parameterized filters."""
from pathlib import Path

import duckdb
import pandas as pd


def query_prices(root: Path, *, start=None, end=None, symbol: str | None = None,
                 series: str | None = None) -> pd.DataFrame:
    files = sorted(str(path) for path in root.glob('year=*/month=*/*.parquet'))
    if not files:
        raise FileNotFoundError(f'No price partitions in {root}')
    conditions, parameters = [], [files]
    for expression, value in [('trade_date >= ?', start), ('trade_date <= ?', end),
                              ('symbol = ?', symbol), ('series = ?', series)]:
        if value is not None:
            conditions.append(expression)
            parameters.append(value)
    where = ' WHERE ' + ' AND '.join(conditions) if conditions else ''
    with duckdb.connect(':memory:') as connection:
        return connection.execute(
            'SELECT * FROM read_parquet(?, hive_partitioning=false, union_by_name=true)' + where
            + ' ORDER BY trade_date, symbol, series', parameters).fetchdf()
