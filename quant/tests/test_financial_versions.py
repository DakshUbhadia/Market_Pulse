from pathlib import Path
import pandas as pd

from quant.config import Config
from quant.data.financial_versions import FinancialVersionStore
from quant.data.nse_client import RawResponse
from quant.features.fundamental_snapshot import fundamental_snapshot
from quant.features.tests.test_fundamental_snapshot import filing
from quant.storage.parquet_store import read_parquet_file


def test_reused_document_url_never_rewrites_original_or_invents_revision_publication(tmp_path):
    config = Config(data_dir=tmp_path)
    store = FinancialVersionStore(config)
    second_writer = FinancialVersionStore(config)  # initialized before the first writer publishes
    raw = RawResponse('https://www.nseindia.com/api/test','2024-08-01T20:00:00+05:30','b'*64,Path('raw.json'),200)
    original = store.publish(pd.DataFrame([filing()]),raw)
    original_bytes = original.read_bytes()
    raw = RawResponse(raw.source_url,'2024-08-05T20:00:00+05:30',raw.sha256,raw.path,200)
    changed = second_writer.publish(pd.DataFrame([filing(document_sha256='c'*64,revenue=999)]),raw)
    assert changed != original and original.read_bytes() == original_bytes
    store = FinancialVersionStore(config)  # detection persists across resumes
    repeated = store.publish(pd.DataFrame([filing(document_sha256='c'*64,revenue=999)]),raw)
    assert repeated == changed
    rows = pd.concat([read_parquet_file(path) for path in (tmp_path/'normalized/financials').rglob('*.parquet')],ignore_index=True)
    assert fundamental_snapshot(rows,'2024-08-02T20:00:00+05:30').revenue.tolist() == [100.]
    assert fundamental_snapshot(rows,'2024-08-06T20:00:00+05:30').empty
    assert original.read_bytes() == original_bytes
