from datetime import date
from unittest.mock import Mock

import pandas as pd

from quant.config import Config
from quant.data.nse_client import RawResponse
from quant.data.http import sha256
from quant.pipeline import update_corporate as pipeline
from quant.pipeline.state import PipelineState
from quant.data.normalization import write_observation


def test_corporate_poll_overlap_preserves_raw_versions(tmp_path, monkeypatch):
    config = Config(data_dir=tmp_path)
    observed = []
    class Client:
        def __enter__(self):
            return self
        def __exit__(self, *_):
            pass
        def get_json(self, path, params, dataset):
            observed.append(params)
            self.last_response = RawResponse('https://www.nseindia.com/api/test',
                '2024-07-09T20:00:00+05:30', 'a' * 64, tmp_path / 'raw.json', 200)
            return [dict(symbol='TEST', isin='INE000000001', subject='Bonus 1:1',
                         exDate='08-Jul-2024', recDate='08-Jul-2024')]
    monkeypatch.setattr(pipeline, 'NseClient', lambda cfg: Client())
    report = pipeline.update_corporate(config, date(2024, 7, 1), date(2024, 7, 9))
    assert report['nse_corporate_actions']['status'] == 'READY'
    assert report['nse_financials']['status'] == 'DISABLED'
    files = list((tmp_path / 'normalized/corporate_actions').rglob('*.parquet'))
    assert len(files) == 1
    pipeline.update_corporate(config, date(2024, 7, 1), date(2024, 7, 9))
    assert len(list((tmp_path / 'normalized/corporate_actions').rglob('*.parquet'))) == 1
    assert observed[-1]['from_date'] == '01-07-2024'


def test_response_versions_are_immutable(tmp_path):
    first = pd.DataFrame([dict(version='first', value=1)])
    second = pd.DataFrame([dict(version='second', value=2)])
    p1 = write_observation(first, tmp_path, sha256(b'first'), '2024-07-08T20:00:00+05:30')
    p2 = write_observation(second, tmp_path, sha256(b'second'), '2024-07-08T20:00:00+05:30')
    assert p1 != p2 and pd.read_parquet(p1).value.iloc[0] == 1


def test_state_instances_preserve_other_stages(tmp_path):
    config = Config(data_dir=tmp_path)
    older = PipelineState(config)
    newer = PipelineState(config)
    newer.record('prices', status='READY', day='2024-07-08')
    older.record('corporate', status='READY', checked_through='2024-07-09')
    assert set(PipelineState(config).data) == {'prices', 'corporate'}
