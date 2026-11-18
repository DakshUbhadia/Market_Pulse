"""Assemble dated, model-bound monitoring evidence without retraining or promotion."""
import argparse
from datetime import datetime, timezone
from pathlib import Path
import json
import pandas as pd

from quant.forward.signal_store import content_hash, read_signals
from quant.monitoring.feature_drift import feature_drift, rank_turnover
from quant.monitoring.factor_ic import factor_ic_drift
from quant.monitoring.coverage import coverage_health
from quant.monitoring.portfolio_risk import portfolio_risk
from quant.monitoring.data_freshness import data_freshness
from quant.storage.parquet_store import read_parquet_file
from quant.storage.research_store import digest_file, write_json


def research_monitoring(*, root, as_of, reference, current, features, reference_ic,
                        current_ic, curve, source_health, coverage, cluster_weights, incidents):
    batches, signals = read_signals(root)
    batches = [b for b in batches if b['as_of'] <= str(as_of)]
    cards = {b['settings'].get('model_card_sha256') for b in batches}
    if len(cards) != 1 or None in cards:
        raise ValueError('Monitoring requires one immutable registered model card per cohort')
    for frame, column in ((reference, 'as_of'), (current, 'as_of'), (curve, 'trade_date')):
        if pd.to_datetime(frame[column]).gt(pd.Timestamp(as_of)).any():
            raise ValueError('Monitoring inputs contain observations after the reporting cutoff')
    if not reference.empty and not current.empty and pd.to_datetime(reference.as_of).max() >= pd.to_datetime(current.as_of).min():
        raise ValueError('Feature drift reference must precede the current observation window')
    panels = dict(feature_drift=feature_drift(reference, current, features=features),
        factor_ic=factor_ic_drift(reference_ic, current_ic, as_of=as_of),
        coverage=coverage_health(**coverage), portfolio_risk=portfolio_risk(curve, cluster_weights=cluster_weights),
        freshness=data_freshness(source_health['sources'], required_session=as_of))
    ic_rows = panels['factor_ic']['factors']
    statuses = [v['status'] for k, v in panels.items() if k != 'factor_ic']+[r['status'] for r in ic_rows]
    if not ic_rows:
        statuses.append('UNASSESSED')
    if any(not isinstance(incidents.get(k), int) or incidents[k] < 0 for k in ('data', 'lifecycle', 'transition', 'accounting')):
        raise ValueError('All incident dimensions require assessed nonnegative counts')
    unresolved = sum(incidents.values())
    # Signals and next-session shadow records must both exist before integrity passes.
    shadow = {}
    for path in (Path(root)/'shadow').glob('*.json'):
        if path.stem > str(as_of):
            continue
        row = json.loads(path.read_text(encoding='utf-8'))
        if row.get('sha256') != content_hash({k: v for k, v in row.items() if k != 'sha256'}):
            raise ValueError('Monitoring shadow evidence checksum changed')
        shadow[path.stem] = row
    expected_dates = {str(pd.Timestamp(d).date()) for d in curve.trade_date}
    if curve.trade_date.duplicated().any():
        raise ValueError('Monitoring NAV observations must have unique session dates')
    actual_curve = {str(pd.Timestamp(r['trade_date']).date()): r for r in curve.to_dict('records')}
    curve_matches = bool(expected_dates) and expected_dates == set(shadow)
    if curve_matches:
        curve_matches = all(abs(actual_curve[d]['nav']-r['equity']['nav']) < 1e-6
            and abs(actual_curve[d]['daily_return']-r['equity']['daily_return']) < 1e-12 for d, r in shadow.items())
    signals_covered = all(b['as_of'] in shadow for b in batches)
    shadow_matches = all(r.get('signal_batches') == [b['sha256'] for b in batches if b['as_of'] <= d]
                         for d, r in shadow.items())
    integrity = bool(batches and shadow and max(shadow) == str(as_of) and unresolved == 0
                     and curve_matches and signals_covered and shadow_matches)
    signals = signals[pd.to_datetime(signals.as_of).le(pd.Timestamp(as_of))] if len(signals) else signals
    dates = sorted(pd.to_datetime(signals.as_of).unique()) if len(signals) else []
    turnover = rank_turnover(signals[signals.as_of.eq(dates[-2])], signals[signals.as_of.eq(dates[-1])]) if len(dates) >= 2 else None
    status = 'PASS' if integrity and statuses and all(s == 'PASS' for s in statuses) else 'REVIEW_REQUIRED'
    return dict(status=status, as_of=str(as_of), generated_at=datetime.now(timezone.utc).isoformat(),
        model_card_sha256=next(iter(cards)), cohort_root=str(Path(root).resolve()), panels=panels,
        incidents=incidents, unresolved_incidents=unresolved, operational_integrity=integrity,
        rank_turnover=turnover, automatic_retraining=False, automatic_promotion=False,
        cohort_evidence_sha256=content_hash([b['sha256'] for b in batches]))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--as-of', required=True)
    for key in ('reference', 'current', 'reference-ic', 'current-ic', 'curve', 'observations', 'output'):
        parser.add_argument('--'+key, type=Path, required=True)
    parser.add_argument('--features', nargs='+', required=True)
    args = parser.parse_args()
    observations = json.loads(args.observations.read_text(encoding='utf-8'))
    inputs = [args.reference, args.current, args.reference_ic, args.current_ic, args.curve]
    frames = [read_parquet_file(p) for p in inputs]
    report = research_monitoring(root=args.root, as_of=args.as_of, reference=frames[0], current=frames[1],
        features=args.features, reference_ic=frames[2], current_ic=frames[3], curve=frames[4], **observations)
    report['input_sha256'] = {str(p): digest_file(p) for p in [*inputs, args.observations]}
    write_json(args.output, report)
    print(json.dumps(report, indent=2))
    return 0 if report['status'] == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
