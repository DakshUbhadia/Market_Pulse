from datetime import datetime, timezone
from uuid import uuid4

from quant.storage.parquet_store import write_parquet
from quant.storage.research_store import write_json
from quant.data.http import atomic_write


def seal_backtest(path):
    """Written last, after all diagnostics/windows; incomplete runs have no seal."""
    from quant.storage.research_store import digest_file
    files = {item.relative_to(path).as_posix(): digest_file(item)
             for item in sorted(path.rglob('*')) if item.is_file() and item != path/'completion.json'}
    from quant.forward.signal_store import append_record
    append_record(path/'completion.json', dict(status='COMPLETE', files=files))


def verify_backtest_seal(path):
    import json
    from pathlib import Path
    from quant.storage.research_store import digest_file
    path = Path(path).resolve()
    seal = json.loads((path/'completion.json').read_text(encoding='utf-8'))
    current = {item.relative_to(path).as_posix() for item in path.rglob('*')
               if item.is_file() and item != path/'completion.json'}
    if seal.get('status') != 'COMPLETE' or set(seal.get('files', {})) != current:
        raise ValueError('Backtest artifact set is incomplete or changed')
    for name, expected in seal['files'].items():
        item = (path/name).resolve()
        if not item.is_relative_to(path) or digest_file(item) != expected:
            raise ValueError('Frozen backtest artifact checksum changed')
    return seal


def save_backtest(root, *, config, metrics, result, ic, deciles, rolling, evidence, extra=None):
    path = root / ('run-' + datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S') + '-' + uuid4().hex[:8])
    path.mkdir(parents=True, exist_ok=False)
    write_json(path / 'config.json', config)
    write_json(path / 'metrics.json', dict(performance=metrics, evidence=evidence, limitations=result.limitations))
    for name, frame in [('equity_curve', result.equity_curve), ('trades', result.trades),
                         ('holdings', result.holdings), ('ic', ic), ('deciles', deciles), ('rolling_excess', rolling)]:
        write_parquet(frame, path / f'{name}.parquet')
    write_parquet(result.skipped_orders, path / 'skipped_orders.parquet')
    write_parquet(result.dividends, path / 'dividends.parquet')
    write_parquet(result.lifecycle, path / 'lifecycle.parquet')
    write_parquet(result.security_transitions, path / 'security-transitions.parquet')
    if extra is not None:
        write_json(path / 'robustness.json', extra)
    report = ('# Factor V1 research report\n\n'
              f'Evidence status: {evidence["status"]}. Public recommendations remain disabled.\n\n'
              f'Evidence policy: {config.get("evidence_policy_version", "UNVERSIONED")}. '
              f'Lifecycle policy/scenario: {config.get("lifecycle_policy_version", "UNVERSIONED")} / '
              f'{config.get("lifecycle_scenario", "UNSPECIFIED")}.\n\n'
              f'Score percentiles are ranks, not profit probabilities. Return basis: {config.get("return_basis", "PRICE")}.\n\n'
              + '\n'.join(f'- {key}: {value}' for key, value in metrics.items()) + '\n\n'
              + '\n'.join(f'- {key}: {"PASS" if value else "UNMET"}' for key, value in evidence['checks'].items())
              + '\n\n' + '\n'.join(f'- {item}' for item in result.limitations) + '\n')
    atomic_write(path / 'report.md', report.encode())
    return path
