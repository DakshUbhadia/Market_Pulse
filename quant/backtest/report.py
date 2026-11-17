"""Evidence gates report unmet or unmeasurable criteria instead of assuming success."""
import numpy as np
import pandas as pd
from quant.backtest.validation import validation_levels
from quant.version import EVIDENCE_POLICY_VERSION

BASELINE_METRICS = ('annualized_excess_return','information_ratio','Sharpe','max_drawdown','turnover')
BASELINE_DIAGNOSTIC_RULE = 'DIAGNOSTIC_ONLY_LEGACY_GATE_UNCHANGED'


def baseline_comparison(metrics, baselines):
    """Predeclared diagnostics; legacy promotion gates remain unchanged."""
    rows = []
    for name, measured in sorted((baselines or {}).items()):
        row = dict(baseline=name, evidence_policy_version=EVIDENCE_POLICY_VERSION,
                   rule=BASELINE_DIAGNOSTIC_RULE)
        for key in BASELINE_METRICS:
            strategy, baseline = metrics.get(key), measured.get(key)
            valid = strategy is not None and baseline is not None and np.isfinite([strategy,baseline]).all()
            row.update({f'strategy_{key}':strategy,f'baseline_{key}':baseline,
                        f'difference_{key}':float(strategy-baseline) if valid else None})
        row['assessed'] = all(row[f'difference_{key}'] is not None for key in BASELINE_METRICS)
        rows.append(row)
    return rows


def evaluate_evidence(metrics, ic_summary, deciles, cost_stress, curve, benchmark, *,
                      costs_verified, sector_concentration=None, baselines=None, cluster_concentration=None,
                      clusters_assessed=False, pit_data_verified=False, forward_test_completed=False,
                      recommendation_history_tracked=False):
    values = deciles.groupby('decile').excess_return.mean() if not deciles.empty else pd.Series(dtype=float)
    monotonic = values.index.to_series().corr(values.rank()) if len(values) == 10 else np.nan
    returns = curve.set_index('trade_date').daily_return
    aligned = benchmark.reindex(returns.index)
    if aligned.isna().any():
        raise ValueError('Missing benchmark sessions in yearly evidence')
    yearly = (1 + returns).resample('YE').prod() - (1 + aligned).resample('YE').prod()
    positive = yearly.clip(lower=0)
    dominance = positive.max()/positive.sum() if positive.sum() > 0 and len(yearly) >= 3 else np.nan
    conditions = dict(
        positive_OOS_excess=metrics.get('annualized_excess_return', 0) > 0,
        positive_mean_IC=(ic_summary.get('mean_IC') or 0) > 0,
        positive_median_IC=(ic_summary.get('median_IC') or 0) > 0,
        majority_positive_IC=(ic_summary.get('positive_IC_fraction') or 0) >= .55,
        monotonic_deciles=bool(np.isfinite(monotonic) and monotonic >= .7 and values.iloc[-1] > values.iloc[0]),
        positive_net_performance=metrics.get('annualized_return', 0) > 0,
        survives_1_5x_costs=cost_stress.get('annualized_excess_return', 0) > 0,
        diversified_across_years=bool(np.isfinite(dominance) and dominance <= .5),
        diversified_across_sectors=sector_concentration is not None and sector_concentration <= .4,
        diversified_across_clusters=bool(clusters_assessed and cluster_concentration is not None and cluster_concentration <= .4),
        manageable_turnover=metrics.get('turnover', float('inf')) <= 12,
        reasonable_drawdown=metrics.get('max_drawdown', -1) >= -.4,
        OOS_IR_above_0_5=(metrics.get('information_ratio') or 0) > .5,
        net_Sharpe_above_0_7=(metrics.get('Sharpe') or 0) > .7,
        adequate_OOS_length=metrics.get('observations', 0) >= 504,
        mature_label_coverage=(ic_summary.get('label_coverage') or 0) >= .995,
        verified_cost_schedule=costs_verified,
        beats_simple_baselines=bool(baselines) and len(baselines) == 5 and all(
            metrics.get('total_return', -1) > row.get('total_return', row.get('cumulative_price_return', float('inf')))
            for row in (baselines or {}).values()),
    )
    levels = validation_levels(conditions, acceptable_drawdown=metrics.get('max_drawdown',-1) >= -.4,
        pit_data_verified=pit_data_verified, forward_test_completed=forward_test_completed,
        recommendation_history_tracked=recommendation_history_tracked)
    research_checks = {key:value for key,value in conditions.items() if key != 'diversified_across_sectors'}
    return dict(status='PASSES_RESEARCH_HURDLES' if all(research_checks.values()) else 'NOT_VALIDATED',
                evidence_policy_version=EVIDENCE_POLICY_VERSION,
                baseline_comparison=baseline_comparison(metrics,baselines),
                legacy_beats_all_baselines=conditions['beats_simple_baselines'],
                checks=conditions, decile_monotonicity=monotonic, largest_positive_year_fraction=dominance,
                validation_levels=levels,
                highest_validation_level=next((name for name in reversed(list(levels)) if levels[name]['passed']), 'NOT_VALIDATED'),
                cluster_check='ASSESSED' if clusters_assessed else 'UNASSESSED_OR_INCOMPLETE',
                sector_check='UNASSESSED_NO_PIT_CLASSIFICATION' if sector_concentration is None else 'ASSESSED',
                public_recommendations_allowed=False, ML_authorized=False)
