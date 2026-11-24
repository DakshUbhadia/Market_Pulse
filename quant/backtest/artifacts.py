from datetime import datetime, timezone
from uuid import uuid4

from quant.storage.parquet_store import write_parquet
from quant.storage.research_store import write_json
from quant.data.http import atomic_write


def seal_backtest(path):
    """Written last, after all diagnostics/windows; incomplete runs have no seal."""
    from quant.storage.research_store import digest_file
    from quant.research.authority import reject_diagnostic_artifacts
    reject_diagnostic_artifacts(path)
    import json
    if (path/'config.json').is_file():
        config = json.loads((path/'config.json').read_text(encoding='utf-8'))
        if str(config.get('model_version', '')).startswith('factor_v1'):
            from quant.governance.gates import GateRegistry, data_root_for
            GateRegistry(data_root_for(path)).require('V1_SEAL')
    files = {item.relative_to(path).as_posix(): digest_file(item)
             for item in sorted(path.rglob('*')) if item.is_file() and item != path/'completion.json'}
    from quant.forward.signal_store import append_record
    append_record(path/'completion.json', dict(status='COMPLETE', files=files))


def verify_backtest_seal(path):
    import json
    from pathlib import Path
    from quant.storage.research_store import digest_file
    path = Path(path).resolve()
    from quant.research.authority import reject_diagnostic_artifacts
    reject_diagnostic_artifacts(path)
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
    if config.get('research_authority') == 'DIAGNOSTIC_ONLY':
        from quant.forward.signal_store import append_record
        append_record(path/'diagnostic-authority.json', dict(research_authority='DIAGNOSTIC_ONLY',
            seal_eligible=False, historical_validation=False, promotion_eligible=False,
            governance_gate=config.get('governance_gate'), governance_status=config.get('governance_status')))
    write_json(path / 'metrics.json', dict(performance=metrics, evidence=evidence, limitations=result.limitations))
    for name, frame in [('equity_curve', result.equity_curve), ('trades', result.trades),
                         ('holdings', result.holdings), ('ic', ic), ('deciles', deciles), ('rolling_excess', rolling)]:
        write_parquet(frame, path / f'{name}.parquet')
    write_parquet(result.skipped_orders, path / 'skipped_orders.parquet')
    write_parquet(result.dividends, path / 'dividends.parquet')
    write_parquet(result.lifecycle, path / 'lifecycle.parquet')
    write_parquet(result.security_transitions, path / 'security-transitions.parquet')
    write_parquet(result.target_orders, path / 'target-orders.parquet')
    if extra is not None:
        write_json(path / 'robustness.json', extra)
    heading = 'Factor V1 diagnostic report' if config.get('research_authority') == 'DIAGNOSTIC_ONLY' else 'Factor V1 research report'
    report = (f'# {heading}\n\n'
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


def complete_diagnostic(path, *, reason, governance_status):
    """An integrity inventory is deliberately separate from a historical seal."""
    from quant.forward.signal_store import append_record
    from quant.storage.research_store import digest_file
    if any((path/name).exists() for name in ('completion.json', 'v1-decision.json', 'v2-decision.json')):
        raise ValueError('Diagnostic outputs must not contain a research seal or decision')
    files = {p.relative_to(path).as_posix(): digest_file(p) for p in sorted(path.rglob('*'))
             if p.is_file() and p != path/'diagnostic-completion.json'}
    record = dict(status='DIAGNOSTIC_COMPLETE', research_authority='DIAGNOSTIC_ONLY',
        seal_eligible=False, historical_validation=False, promotion_eligible=False,
        real_forward_evidence=False, reason=reason, governance_status=governance_status, files=files)
    append_record(path/'diagnostic-completion.json', record)
    return record


def verify_diagnostic_completion(path):
    import json
    from pathlib import Path
    from quant.storage.research_store import digest_file
    path = Path(path).resolve()
    record = json.loads((path/'diagnostic-completion.json').read_text(encoding='utf-8'))
    actual = {p.relative_to(path).as_posix() for p in path.rglob('*') if p.is_file() and p != path/'diagnostic-completion.json'}
    if (record.get('status') != 'DIAGNOSTIC_COMPLETE' or record.get('research_authority') != 'DIAGNOSTIC_ONLY'
            or any(record.get(k) is not False for k in ('seal_eligible', 'historical_validation', 'promotion_eligible', 'real_forward_evidence'))
            or set(record.get('files', {})) != actual
            or any((path/name).exists() for name in ('completion.json', 'v1-decision.json', 'v2-decision.json'))):
        raise ValueError('Invalid diagnostic completion inventory')
    for name, expected in record['files'].items():
        source = (path/name).resolve()
        if not source.is_relative_to(path) or source.is_symlink() or digest_file(source) != expected:
            raise ValueError('Diagnostic artifact checksum changed')
    return record
