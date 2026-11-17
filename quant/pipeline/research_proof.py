"""Reuse an audited readiness result only while every input and gate source matches.

Checksums include raw prices, adjustments, benchmarks, actions, identity evidence,
calendar, pipeline state and the gate's implementation. Newly added or removed
partitions invalidate the proof. Report files and model outputs are not inputs.
"""
import json
import importlib.metadata
from datetime import datetime, timezone
from uuid import uuid4

from quant.storage.research_store import digest_file, write_json
from quant.data.http import atomic_write
from quant.storage.parquet_store import read_parquet_file

GATE_SOURCES = ('boundaries.py','universe/config.py','pipeline/check_research_ready.py',
    'pipeline/research_proof.py','pipeline/audit_prices.py','pipeline/update_calendar.py',
    'features/adjustments.py','data/security_history.py','data/nse_calendar.py','data/nse_bhavcopy.py',
    'pipeline/audit_lifecycle.py','pipeline/backfill_lifecycle.py','lifecycle/schema.py','lifecycle/state.py','lifecycle/policy.py',
    'storage/parquet_store.py')


def fingerprint_inputs(config, as_of):
    from quant.config import REPO_ROOT
    files = []
    for dataset in ('prices','adjusted_prices','indices','corporate_actions','lifecycle'):
        for path in sorted((config.data_dir/'normalized'/dataset).rglob('*.parquet')):
            if dataset in ('corporate_actions','lifecycle') or path.stem <= str(as_of):
                files.append(path)
    import pandas as pd
    lifecycle_path = config.data_dir/'normalized/lifecycle/events.parquet'
    if lifecycle_path.exists():
        try:
            lifecycle = read_parquet_file(lifecycle_path)
            files.extend(config.data_dir/path for path in lifecycle.get('raw_path',pd.Series(dtype=str)).dropna().unique()
                if (config.data_dir/path).resolve().is_relative_to(config.data_dir.resolve()))
        except (OSError,ValueError):
            pass  # The evidence audit reports malformed normalized data; retain its file digest.
    files += [config.calendar_path, config.data_dir/'normalized/security_history/identities.parquet']
    state_path = config.data_dir/'state/pipeline_state.json'
    state = json.loads(state_path.read_text()) if state_path.exists() else {}
    return dict(inputs={str(path.relative_to(config.data_dir)):digest_file(path) for path in files if path.is_file()},
        pipeline_state={key:state.get(key) for key in ('adjusted_prices','nse_corporate_actions','lifecycle')},
        dependencies={name:importlib.metadata.version(name) for name in ('numpy','pandas','pyarrow')},
        gate_sources={name:digest_file(REPO_ROOT/'quant'/name) for name in GATE_SOURCES})


def save_readiness_proof(config, result, fingerprint=None):
    from quant.boundaries import RAW_PRICE_START
    if result['status'] != 'READY' or result.get('full_history_start') != str(RAW_PRICE_START):
        return
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S') + '-' + uuid4().hex[:8]
    proof = dict(result=result, fingerprint=fingerprint or fingerprint_inputs(config,result['as_of']))
    path = config.data_dir / 'research/integrity' / stamp
    path.mkdir(parents=True,exist_ok=False)
    write_json(path/'readiness.json',result)
    write_json(path/'proof.json',proof)
    for pattern in ('price-audit-*.json','fundamentals-audit-*.json','tri-coverage.json'):
        reports = sorted((config.data_dir/'reports').glob(pattern))
        if reports:
            atomic_write(path/reports[-1].name,reports[-1].read_bytes())
    write_json(config.data_dir/'state/research-readiness-proof.json',proof)
    return path


def cached_readiness(config, as_of, requested_start, minimum):
    from quant.boundaries import RAW_PRICE_START
    path = config.data_dir/'state/research-readiness-proof.json'
    try:
        proof = json.loads(path.read_text())
        result = proof['result']
        if (result['status'] != 'READY' or result['as_of'] != str(as_of)
                or result.get('full_history_start') != str(RAW_PRICE_START)
                or str(requested_start) > str(as_of)
                or result['min_history_sessions'] != minimum or not result['first_possible_signal_date']
                or str(requested_start) < result['first_possible_signal_date']
                or result['identity_gaps_after_boundary']
                or fingerprint_inputs(config,as_of) != proof['fingerprint']):
            return None
        return dict(result, requested_backtest_start=str(requested_start), reused_verified_proof=True)
    except (OSError,ValueError,KeyError,TypeError):
        return None
