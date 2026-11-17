import pandas as pd

from quant.tests.research_fixtures import market_fixture
from quant.features.matrix import build_feature_matrix
from quant.storage.parquet_store import write_parquet
from quant.storage.research_store import digest_file


def test_identical_feature_inputs_produce_identical_content_and_bytes(tmp_path):
    prices,benchmark,sessions = market_fixture(stocks=3,days=300)
    left = build_feature_matrix(prices,benchmark,sessions)
    right = build_feature_matrix(prices,benchmark,sessions)
    assert 'generated_at' not in left
    pd.testing.assert_frame_equal(left,right)
    write_parquet(left,tmp_path/'left.parquet')
    write_parquet(right,tmp_path/'right.parquet')
    assert digest_file(tmp_path/'left.parquet') == digest_file(tmp_path/'right.parquet')
