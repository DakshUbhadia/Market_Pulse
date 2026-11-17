"""Forward counts are diagnostics, never an automatic production promotion."""
import json
from pathlib import Path

import pandas as pd

from quant.forward.signal_store import read_signals, content_hash


def forward_metrics(root):
    batches, signals = read_signals(root)
    outcomes = [json.loads(path.read_text(encoding='utf-8')) for path in (Path(root)/'outcomes').glob('*/*.json')]
    for row in outcomes:
        if content_hash({k:v for k,v in row.items() if k != 'sha256'}) != row['sha256']:
            raise ValueError('Frozen forward outcome checksum changed')
    frame = pd.DataFrame(outcomes)
    summary = {}
    for horizon in (21,63):
        rows = frame[frame.horizon_sessions.eq(horizon)] if not frame.empty else frame
        summary[str(horizon)] = dict(matured_outcomes=len(rows), distinct_signals=rows.signal_id.nunique() if len(rows) else 0,
            mean_cost_adjusted_excess=float(rows.cost_adjusted_excess_return.mean()) if len(rows) else None)
    from quant.backtest.engine import monthly_signal_dates
    days = pd.DatetimeIndex(pd.to_datetime([b['as_of'] for b in batches]))
    shadow_days = {p.stem for p in (Path(root)/'shadow').glob('*.json')}
    rebalance_dates = monthly_signal_dates(days) if len(days) else set()
    shadow = [json.loads(p.read_text(encoding='utf-8')) for p in (Path(root)/'shadow').glob('*.json')]
    buys = {trade['instrument_id'] for row in shadow for trade in row['trades'] if trade['side'] == 'BUY'}
    return dict(validation_level='FORWARD_PAPER_ONLY', production_validated=False,
        signal_sessions=len(batches), distinct_recommendations=len(buys),
        distinct_ranked_instruments=signals.instrument_id.nunique() if len(signals) else 0,
        rebalance_cycles=sum(any(p > str(day.date()) for p in shadow_days) for day in rebalance_dates),
        outcomes=summary, reason='Overlapping 63-session observations are not independent; manual multi-cycle review required')
