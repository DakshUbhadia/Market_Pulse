from datetime import date

from quant.config import Config
from quant.pipeline.research_proof import cached_readiness, save_readiness_proof


def test_audit_proof_detects_mutation_new_partition_and_removed_input(tmp_path):
    config = Config(data_dir=tmp_path)
    source = tmp_path/'normalized/prices/year=2024/month=01/2024-01-02.parquet'
    source.parent.mkdir(parents=True)
    source.write_bytes(b'original checked input')
    result = dict(status='READY',as_of='2024-01-02',full_history_start='2010-01-01',
        min_history_sessions=252,first_possible_signal_date='2012-06-25',identity_gaps_after_boundary=[])
    save_readiness_proof(config,result)
    assert cached_readiness(config,date(2024,1,2),date(2016,1,1),252)
    assert cached_readiness(config,date(2024,1,2),date(2011,1,1),252) is None
    source.write_bytes(b'changed')
    assert cached_readiness(config,date(2024,1,2),date(2016,1,1),252) is None
    source.write_bytes(b'original checked input')
    extra = source.with_name('2024-01-01.parquet')
    extra.write_bytes(b'new partition')
    assert cached_readiness(config,date(2024,1,2),date(2016,1,1),252) is None
    extra.unlink()
    source.unlink()
    assert cached_readiness(config,date(2024,1,2),date(2016,1,1),252) is None


def test_partial_history_cannot_supply_a_full_history_proof(tmp_path):
    result = dict(status='READY',full_history_start='2024-01-01')
    assert save_readiness_proof(Config(data_dir=tmp_path),result) is None
