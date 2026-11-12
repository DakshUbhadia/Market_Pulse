"""Read local price partitions with parameterized filters."""
from pathlib import Path

import duckdb
import pandas as pd

DATASETS = {
    'prices': 'trade_date', 'delivery': 'trade_date', 'adjusted_prices': 'trade_date',
    'instruments': 'snapshot_date', 'corporate_actions': 'ex_date', 'indices': 'trade_date',
    'vix': 'trade_date', 'financials': 'exchange_disseminated_at',
    'shareholding': 'broadcast_at', 'announcements': 'announcement_timestamp',
    'macro': 'publication_date', 'fii_dii': 'trade_date',
}


def dataset_files(data_dir, dataset):
    root = Path(data_dir) / 'normalized' / dataset
    if dataset == 'instruments':
        root = root / 'nse'  # Broker mappings are not the research security master.
    return sorted(str(path) for path in root.rglob('*.parquet'))


def query_dataset(data_dir: Path, dataset: str, *, start=None, end=None, symbol=None):
    """Allowlisted SQL identifiers, bound values, and direct Parquet scans."""
    if dataset not in DATASETS:
        raise ValueError(f'Unknown research dataset: {dataset}')
    files = dataset_files(data_dir, dataset)
    if not files:
        raise FileNotFoundError(f'No {dataset} partitions')
    date_column = DATASETS[dataset]
    conditions, parameters = [], [files]
    for expression, value in [(f'{date_column} >= ?', start), (f'{date_column} <= ?', end),
                              ('symbol = ?', symbol)]:
        if value is not None:
            conditions.append(expression)
            parameters.append(value)
    where = ' WHERE ' + ' AND '.join(conditions) if conditions else ''
    with duckdb.connect(':memory:') as connection:
        return connection.execute('SELECT * FROM read_parquet(?, hive_partitioning=false, union_by_name=true)'
                                  + where, parameters).fetchdf()


def research_connection(data_dir: Path):
    """Caller owns the returned connection; unavailable datasets have no view."""
    connection = duckdb.connect(':memory:')
    for dataset in DATASETS:
        files = dataset_files(data_dir, dataset)
        if files:
            relation = connection.read_parquet(files, hive_partitioning=False, union_by_name=True)
            relation.create_view(dataset)
    return connection


def query_prices(root: Path, *, start=None, end=None, symbol: str | None = None,
                 series: str | None = None, columns=None) -> pd.DataFrame:
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
    allowed = {'trade_date', 'symbol', 'series', 'isin', 'open', 'high', 'low', 'close', 'last',
               'previous_close', 'volume', 'traded_value', 'num_trades', 'source_file', 'source_hash', 'data_quality'}
    if columns is not None and (not columns or not set(columns).issubset(allowed)):
        raise ValueError('Unknown price columns')
    projection = ', '.join('"' + column + '"' for column in columns) if columns else '*'
    with duckdb.connect(':memory:') as connection:
        return connection.execute(
            'SELECT ' + projection + ' FROM read_parquet(?, hive_partitioning=false, union_by_name=true)' + where
            + ' ORDER BY trade_date, symbol, series', parameters).fetchdf()
