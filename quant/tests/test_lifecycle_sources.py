import pandas as pd
import pytest

from quant.data.nse_lifecycle import inventory_links, archive_source
from quant.data.lifecycle_normalize import normalize_events
from quant.backtest.lifecycle import overlay_universe
from quant.backtest.tests.test_lifecycle import event
from quant.config import Config


def test_inventory_discovery_only_accepts_official_exchange_documents():
    content = b'<a href="https://nsearchives.nseindia.com/delisted.xlsx">list</a><a href="https://other.test/x.csv">bad</a>'
    assert inventory_links(content,'https://www.nseindia.in') == ['https://nsearchives.nseindia.com/delisted.xlsx']


def test_foreign_evidence_source_rejected(tmp_path):
    with pytest.raises(ValueError,match='official'):
        archive_source(Config(data_dir=tmp_path),'https://other.test/x.pdf')


def test_universe_overlay_blocks_only_after_publication():
    frame = pd.DataFrame(dict(as_of=pd.to_datetime(['2024-11-04','2024-11-05']),
        instrument_id='id-000',eligible=True,exclusion_reason=''))
    result = overlay_universe(frame,normalize_events([event()]))
    assert result.eligible.tolist() == [True,False]
    assert result.lifecycle_reason.iloc[1] == 'SUSPENDED'


def test_reviewed_import_verifies_source_and_canonical_identity(tmp_path,monkeypatch):
    from quant.pipeline.backfill_lifecycle import ingest_reviewed,load_lifecycle
    from quant.data.security_history import instrument_id
    from quant.data.http import sha256
    raw = tmp_path/'raw/source.pdf'
    raw.parent.mkdir()
    raw.write_bytes(b'official fixture evidence')
    digest = sha256(raw.read_bytes())
    provenance = dict(source_url='https://nsearchives.nseindia.com/test.pdf',source_sha256=digest,
        raw_path='raw/source.pdf',first_seen_at='2026-11-17T00:00:00Z')
    monkeypatch.setattr('quant.pipeline.backfill_lifecycle.archive_source',lambda *args: (raw.read_bytes(),provenance))
    config = Config(data_dir=tmp_path,request_interval=0)
    record = event()
    with pytest.raises(ValueError,match='canonical'):
        ingest_reviewed(config,[record])
    record['instrument_id'] = instrument_id(record['isin'])
    with pytest.raises(ValueError,match='checksum'):
        ingest_reviewed(config,[record])
    record['source_sha256'] = digest
    record['lifecycle_event_id'] = 'stable-event'
    assert len(ingest_reviewed(config,[record])) == 1
    with pytest.raises(ValueError,match='immutable'):
        ingest_reviewed(config,[record])
    assert len(load_lifecycle(config)) == 1
    raw.write_bytes(b'mutated evidence')
    with pytest.raises(ValueError,match='checksum'):
        load_lifecycle(config)
