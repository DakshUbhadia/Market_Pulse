from dataclasses import replace

from quant.backtest.costs import CostModel
from quant.backtest.engine import run_backtest
from quant.backtest.metrics import performance_metrics
from quant.features.matrix import build_feature_matrix
from quant.models.factor_v1 import score_factor_v1


def robustness_runs(prices, scores, benchmark, sessions, *, start, end, portfolio, cost_model,
                    universe_config, benchmark_frame, delivery=None):
    results = {}
    for name, multiplier, slippage, holdings in [
        ('cost_1_5x', 1.5, 1, portfolio.holdings), ('cost_2x', 2, 1, portfolio.holdings),
        ('slippage_1_5x', 1, 1.5, portfolio.holdings), ('slippage_2x', 1, 2, portfolio.holdings),
        ('holdings_20', 1, 1, 20), ('holdings_25', 1, 1, 25), ('holdings_30', 1, 1, 30)]:
        costs = replace(cost_model, cost_multiplier=multiplier, slippage_multiplier=slippage)
        result = run_backtest(prices, scores, sessions, start=start, end=end,
                               portfolio=replace(portfolio, holdings=holdings), cost_model=costs)
        metrics, _ = performance_metrics(result.equity_curve, benchmark, result.trades)
        results[name] = dict(metrics=metrics, cost_multiplier=multiplier, slippage_multiplier=slippage, holdings=holdings)
    for adv in (25_000_000, 50_000_000, 100_000_000):
        cfg = replace(universe_config, min_adv60=adv)
        features = build_feature_matrix(prices, benchmark_frame, sessions, universe_config=cfg, delivery=delivery, eligible_only=True)
        ranked = score_factor_v1(features)
        result = run_backtest(prices, ranked, sessions, start=start, end=end, portfolio=portfolio, cost_model=cost_model)
        metrics, _ = performance_metrics(result.equity_curve, benchmark, result.trades)
        results[f'ADV_{adv}'] = dict(metrics=metrics, min_adv60=adv)
    for medium, long in ((120, 240), (126, 252), (132, 264)):
        features = build_feature_matrix(prices, benchmark_frame, sessions, universe_config=universe_config,
            delivery=delivery, medium_lookback=medium, long_lookback=long, eligible_only=True)
        result = run_backtest(prices, score_factor_v1(features), sessions, start=start, end=end,
                               portfolio=portfolio, cost_model=cost_model)
        metrics, _ = performance_metrics(result.equity_curve, benchmark, result.trades)
        results[f'lookbacks_{medium}_{long}'] = dict(metrics=metrics, medium_lookback=medium, long_lookback=long)
    return results
