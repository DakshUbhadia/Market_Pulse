from datetime import date
import json

from quant.config import Config
from quant.data.http import sha256
from quant.data.nse_client import RawResponse, NseSourceError
from quant.pipeline.backfill_fundamentals import backfill_fundamentals
from quant.storage.parquet_store import read_parquet_file
from quant.tests.test_point_in_time import instance


def test_backfill_resumes_failed_window_preserves_revisions_and_archives_attachments(tmp_path):
    config = Config(data_dir=tmp_path)
    observed = []
    fail = [True]
    xml = instance('<f:RevenueFromOperations contextRef="q" unitRef="INR">123</f:RevenueFromOperations>')
    class Client:
        def __init__(self, _):
            pass
        def __enter__(self):
            return self
        def __exit__(self, *_):
            pass
        def archive(self, content, suffix):
            path = tmp_path/'raw'/f'{sha256(content)}.{suffix}'
            path.parent.mkdir(exist_ok=True)
            path.write_bytes(content)
            self.last_response = RawResponse('https://www.nseindia.com/api/test',
                '2024-09-01T20:00:00+05:30',sha256(content),path,200)
        def get_json(self, path, params, dataset):
            observed.append(params['from_date'])
            if params['from_date'] == '31-07-2024' and fail[0]:
                raise NseSourceError('temporary source failure')
            payload = [dict(symbol='TEST',isin='INE000000001',fromDate='01-Apr-2024',toDate='30-Jun-2024',
                consolidated='Non-Consolidated',bank='N',exchdisstime='01-Aug-2024 16:00:00',
                xbrl='https://nsearchives.nseindia.com/document.xml',attchmntFile='https://nsearchives.nseindia.com/notice.pdf')]
            self.archive(json.dumps(payload).encode(),'json')
            return payload
        def get_bytes(self, url, dataset, suffix):
            content = b'%PDF-fixture' if dataset == 'financial_attachments' else xml
            self.archive(content,suffix)
            return content
    args = dict(window_days=30,revision_overlap_days=0,client_factory=Client)
    first = backfill_fundamentals(config,date(2024,7,1),date(2024,8,31),**args)
    assert first['status'] == 'BLOCKED'
    assert list(first['windows'].values())[0]['status'] == 'COMPLETE'
    assert '30-08-2024' not in observed
    fail[0] = False
    observed.clear()
    second = backfill_fundamentals(config,date(2024,7,1),date(2024,8,31),**args)
    assert second['status'] == 'COMPLETE' and '01-07-2024' not in observed
    files = list((tmp_path/'normalized/financials').rglob('*.parquet'))
    rows = read_parquet_file(files[0])
    assert rows.parser_status.eq('PARSED').all()
    assert rows.attachment_sha256.str.len().eq(64).all()
    assert rows.period_semantics.eq('QUARTER_ONLY').all()
    assert rows.metadata_raw_path.notna().all()
