"""Evidence gates report unmet or unmeasurable criteria instead of assuming success."""
import numpy as np
import pandas as pd


def evaluate_evidence(metrics, ic_summary, deciles, cost_stress, curve, benchmark, *,
                      costs_verified, sector_concentration=None, baselines=None):
    values = deciles.groupby('decile').excess_return.mean() if not deciles.empty else pd.Series(dtype=float)
    monotonic = values.index.to_series().corr(values.rank()) if len(values) == 10 else np.nan
    returns = curve.set_index('trade_date').daily_return
    yearly = (returns - benchmark.reindex(returns.index)).resample('YE').sum()
    positive = yearly.clip(lower=0)
    dominance = positive.max()/positive.sum() if positive.sum() > 0 and len(yearly) >= 3 else np.nan
    conditions = dict(
        positive_OOS_excess=metrics.get('annualized_excess_return', 0) > 0,
        positive_mean_IC=(ic_summary.get('mean_IC') or 0) > 0,
        majority_positive_IC=(ic_summary.get('positive_IC_fraction') or 0) >= .55,
        monotonic_deciles=bool(np.isfinite(monotonic) and monotonic >= .7 and values.iloc[-1] > values.iloc[0]),
        positive_net_performance=metrics.get('annualized_return', 0) > 0,
        survives_1_5x_costs=cost_stress.get('annualized_excess_return', 0) > 0,
        diversified_across_years=bool(np.isfinite(dominance) and dominance <= .5),
        diversified_across_sectors=sector_concentration is not None and sector_concentration <= .4,
        manageable_turnover=metrics.get('turnover', float('inf')) <= 12,
        OOS_IR_above_0_5=(metrics.get('information_ratio') or 0) > .5,
        net_Sharpe_above_0_7=(metrics.get('Sharpe') or 0) > .7,
        adequate_OOS_length=metrics.get('observations', 0) >= 504,
        mature_label_coverage=(ic_summary.get('label_coverage') or 0) >= .995,
        verified_cost_schedule=costs_verified,
        beats_simple_baselines=bool(baselines) and len(baselines) == 5 and all(
            metrics.get('total_return', -1) > row.get('total_return', row.get('cumulative_price_return', float('inf')))
            for row in (baselines or {}).values()),
    )
    return dict(status='PASSES_RESEARCH_HURDLES' if all(conditions.values()) else 'NOT_VALIDATED',
                checks=conditions, decile_monotonicity=monotonic, largest_positive_year_fraction=dominance,
                sector_check='UNASSESSED_NO_PIT_CLASSIFICATION' if sector_concentration is None else 'ASSESSED',
                public_recommendations_allowed=False, ML_authorized=False)
