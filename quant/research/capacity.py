"""Declared capital scenarios through the same next-open risk/accounting engine."""
from dataclasses import replace
from quant.backtest.engine import run_backtest
from quant.backtest.metrics import performance_metrics
from quant.backtest.benchmarks import index_returns, total_return_index_returns
from quant.portfolio.target import risk_target_builder
from quant.research.risk_evidence import risk_evidence


def capacity_scenarios(prices, scores, features, benchmark, sessions, window, *, capitals,
                       portfolio, costs, policy, execution, return_basis):
    reports = []
    for capital in capitals:
        callback, budgets = risk_target_builder(prices, features, sessions, policy)
        result = run_backtest(prices, scores, sessions, start=window['from'], end=window['to'],
            portfolio=replace(portfolio, initial_cash=capital), cost_model=costs,
            target_builder=callback, target_builder_context=True, **execution)
        benchmark_returns = (index_returns(benchmark, result.equity_curve.trade_date) if return_basis == 'PRICE'
            else total_return_index_returns(benchmark, result.equity_curve.trade_date, sessions))
        metrics, _ = performance_metrics(result.equity_curve, benchmark_returns, result.trades)
        evidence = risk_evidence(result, features, budgets, policy, capital, benchmark_returns)
        stressed = []
        for multiplier in (1.5, 2.):
            callback, _ = risk_target_builder(prices, features, sessions, policy)
            stress = run_backtest(prices, scores, sessions, start=window['from'], end=window['to'],
                portfolio=replace(portfolio, initial_cash=capital), cost_model=replace(costs, cost_multiplier=multiplier),
                target_builder=callback, target_builder_context=True, **execution)
            stressed.append(dict(cost_multiplier=multiplier,
                metrics=performance_metrics(stress.equity_curve, benchmark_returns, stress.trades)[0]))
        reports.append(dict(metrics=metrics, risk=evidence, cost_stress=stressed,
                            research_scenario_only=True))
    return reports
