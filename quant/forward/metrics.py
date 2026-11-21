"""Forward counts are diagnostics, never an automatic production promotion."""
import json
from pathlib import Path

import pandas as pd

from quant.forward.signal_store import read_signals, content_hash


def forward_metrics(root, *, as_of=None):
    batches, signals = read_signals(root)
    outcomes = [json.loads(path.read_text(encoding='utf-8')) for path in (Path(root)/'outcomes').glob('*/*.json')]
    for row in outcomes:
        if content_hash({k:v for k,v in row.items() if k != 'sha256'}) != row['sha256']:
            raise ValueError('Frozen forward outcome checksum changed')
        kinds = {b.get('cohort_type', 'REAL') for b in batches}
        if len(kinds) != 1 or row.get('cohort_type', 'REAL') not in kinds:
            raise ValueError('TEST_ONLY outcomes cannot become real forward evidence')
    if as_of is not None:
        outcomes = [r for r in outcomes if pd.Timestamp(r['exit_date']) <= pd.Timestamp(as_of)]
        batches = [b for b in batches if pd.Timestamp(b['as_of']) <= pd.Timestamp(as_of)]
        if len(signals):
            signals = signals[pd.to_datetime(signals.as_of) <= pd.Timestamp(as_of)]
    frame = pd.DataFrame(outcomes)
    summary = {}
    for horizon in (21,63):
        rows = frame[frame.horizon_sessions.eq(horizon)] if not frame.empty else frame
        summary[str(horizon)] = dict(matured_outcomes=len(rows), distinct_signals=rows.signal_id.nunique() if len(rows) else 0,
            mean_cost_adjusted_excess=float(rows.cost_adjusted_excess_return.mean()) if len(rows) else None)
        summary[str(horizon)]['rank_IC'] = None
        if len(rows) and len(signals):
            matched = signals[['signal_id', 'as_of', 'score']].merge(rows, on='signal_id', validate='one_to_one')
            ics = [g.score.rank().corr(g.excess_return.rank()) for _, g in matched.groupby('as_of')
                   if len(g) >= 10 and g.score.nunique() > 1 and g.excess_return.nunique() > 1]
            summary[str(horizon)]['rank_IC'] = float(pd.Series(ics).mean()) if ics else None
    from quant.backtest.engine import monthly_signal_dates
    days = pd.DatetimeIndex(pd.to_datetime([b['as_of'] for b in batches]))
    shadow_days = {p.stem for p in (Path(root)/'shadow').glob('*.json')}
    rebalance_dates = monthly_signal_dates(days) if len(days) else set()
    shadow = [json.loads(p.read_text(encoding='utf-8')) for p in (Path(root)/'shadow').glob('*.json')]
    for row in shadow:
        if row.get('sha256') != content_hash({k: v for k, v in row.items() if k != 'sha256'}):
            raise ValueError('Frozen shadow checksum changed')
    if as_of is not None:
        shadow = [r for r in shadow if pd.Timestamp(r['as_of']) <= pd.Timestamp(as_of)]
        shadow_days = {str(r['as_of']) for r in shadow}
    buys = {trade['instrument_id'] for row in shadow for trade in row['trades'] if trade['side'] == 'BUY'}
    test_only = bool(batches) and all(b.get('cohort_type', 'REAL') == 'TEST_ONLY' for b in batches)
    return dict(validation_level='TEST_ONLY' if test_only else 'FORWARD_PAPER_ONLY', production_validated=False,
        cohort_type='TEST_ONLY' if test_only else 'REAL', real_forward_evidence=not test_only and bool(batches),
        promotion_eligible=False,
        signal_sessions=len(batches), distinct_recommendations=len(buys),
        distinct_ranked_instruments=signals.instrument_id.nunique() if len(signals) else 0,
        rebalance_cycles=sum(any(p > str(day.date()) for p in shadow_days) for day in rebalance_dates),
        outcomes=summary, reason='Overlapping 63-session observations are not independent; manual multi-cycle review required')
