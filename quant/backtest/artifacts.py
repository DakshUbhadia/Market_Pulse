from datetime import datetime, timezone
from uuid import uuid4

from quant.storage.parquet_store import write_parquet
from quant.storage.research_store import write_json
from quant.data.http import atomic_write


def save_backtest(root, *, config, metrics, result, ic, deciles, rolling, evidence, extra=None):
    path = root / ('run-' + datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S') + '-' + uuid4().hex[:8])
    path.mkdir(parents=True, exist_ok=False)
    write_json(path / 'config.json', config)
    write_json(path / 'metrics.json', dict(performance=metrics, evidence=evidence, limitations=result.limitations))
    for name, frame in [('equity_curve', result.equity_curve), ('trades', result.trades),
                         ('holdings', result.holdings), ('ic', ic), ('deciles', deciles), ('rolling_excess', rolling)]:
        write_parquet(frame, path / f'{name}.parquet')
    write_parquet(result.skipped_orders, path / 'skipped_orders.parquet')
    if extra is not None:
        write_json(path / 'robustness.json', extra)
    report = ('# Factor V1 research report\n\n'
              f'Evidence status: {evidence["status"]}. Public recommendations remain disabled.\n\n'
              'Score percentiles are ranks, not profit probabilities. Returns use the explicitly recorded price-return basis.\n\n'
              + '\n'.join(f'- {key}: {value}' for key, value in metrics.items()) + '\n\n'
              + '\n'.join(f'- {key}: {"PASS" if value else "UNMET"}' for key, value in evidence['checks'].items())
              + '\n\n' + '\n'.join(f'- {item}' for item in result.limitations) + '\n')
    atomic_write(path / 'report.md', report.encode())
    return path
