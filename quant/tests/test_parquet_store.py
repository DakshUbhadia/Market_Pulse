import pandas as pd
import pytest

from quant.storage.parquet_store import read_parquet_file, write_parquet


@pytest.mark.usefixtures('hive_partition_reads')
def test_daily_file_round_trip_does_not_persist_inferred_partition_columns(tmp_path):
    path = tmp_path/'year=2024/month=01/2024-01-02.parquet'
    expected = pd.DataFrame(dict(trade_date=pd.to_datetime(['2024-01-02']),value=[1.]))
    write_parquet(expected,path)
    # Reproduce the behavior that polluted rewritten partitions in CI.
    assert {'year','month'}.issubset(pd.read_parquet(path))
    actual = read_parquet_file(path)
    pd.testing.assert_frame_equal(actual,expected)
    write_parquet(actual,path)
    pd.testing.assert_frame_equal(read_parquet_file(path),expected)
    pd.testing.assert_frame_equal(read_parquet_file(path,columns=['value']),expected[['value']])


@pytest.mark.usefixtures('hive_partition_reads')
def test_physical_year_column_is_read_without_merging_hive_dictionary(tmp_path):
    path = tmp_path/'year=2024/month=01/2024-01-02.parquet'
    expected = pd.DataFrame(dict(year=pd.Series([2024],dtype='int32'),value=[1.]))
    write_parquet(expected,path)
    pd.testing.assert_frame_equal(read_parquet_file(path),expected)
