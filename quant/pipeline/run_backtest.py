"""Gated, reproducible V1 research and rolling OOS evaluation; no publishing."""
import json
from datetime import date

import pandas as pd

from quant.backtest.engine import run_backtest
from quant.backtest.portfolio import PortfolioConfig
from quant.backtest.costs import CostModel, SOURCES
from quant.backtest.benchmarks import index_returns, baseline_target
from quant.backtest.metrics import performance_metrics, diagnostics
from quant.backtest.bootstrap import block_bootstrap
from quant.backtest.walk_forward import walk_forward, rolling_windows
from quant.backtest.robustness import robustness_runs
from quant.backtest.report import evaluate_evidence
from quant.backtest.artifacts import save_backtest
from quant.features.matrix import build_feature_matrix
from quant.features.labels import forward_labels
from quant.models.factor_v1 import score_factor_v1
from quant.universe.config import UniverseConfig
from quant.pipeline.check_research_ready import require_research_ready
from quant.storage.research_store import input_manifest, load_research_data, write_json, verify_manifest
from quant.version import MODEL_VERSION, FEATURE_VERSION, COST_MODEL_VERSION


def run_research(config, start, end, *, estimate_historical_costs=False, full_robustness=True):
    readiness = require_research_ready(config, end)
    manifest = input_manifest(config, end)
    prices, benchmark_frame, sessions, delivery, indices = load_research_data(config, end)
    universe, portfolio = UniverseConfig(), PortfolioConfig()
    costs = CostModel(allow_estimated_history=estimate_historical_costs)
    features = build_feature_matrix(prices, benchmark_frame, sessions, universe_config=universe, delivery=delivery, eligible_only=True)
    scores = score_factor_v1(features)
    labels = forward_labels(prices, benchmark_frame, sessions, signal_keys=scores[['as_of','instrument_id']])
    result = run_backtest(prices, scores, sessions, start=start, end=end, portfolio=portfolio, cost_model=costs)
    market = index_returns(benchmark_frame, result.equity_curve.trade_date)
    metrics, rolling = performance_metrics(result.equity_curve, market, result.trades)
    test_scores = scores[scores.as_of.between(pd.Timestamp(start), pd.Timestamp(end))]
    ic, deciles, ic_summary = diagnostics(test_scores, labels)
    metrics.update(ic_summary)
    uncertainty = block_bootstrap(ic.IC if not ic.empty else [])
    baselines = {}
    for name in ('NIFTY 50', 'NIFTY 500'):
        returns = index_returns(indices[indices.index_name == name], result.equity_curve.trade_date)
        baselines[name] = {'cumulative_price_return': float((1+returns).prod()-1), 'basis': 'GROSS_PRICE_INDEX'}
    for name in ('liquid_equal_weight', 'momentum_12_1_top25', 'inverse_volatility'):
        alternative = run_backtest(prices, features, sessions, start=start, end=end, portfolio=portfolio,
                                   cost_model=costs, target_builder=baseline_target(name))
        baselines[name], _ = performance_metrics(alternative.equity_curve, market, alternative.trades)
    stress = robustness_runs(prices, scores, market, sessions, start=start, end=end, portfolio=portfolio,
        cost_model=costs, universe_config=universe, benchmark_frame=benchmark_frame, delivery=delivery) if full_robustness else {}
    evidence = evaluate_evidence(metrics, ic_summary, deciles, stress.get('cost_1_5x', {}).get('metrics', {}),
        result.equity_curve, market, costs_verified=not any('ESTIMATED' in item for item in result.limitations), baselines=baselines)
    verify_manifest(config, manifest)
    run_config = dict(**manifest, model_version=MODEL_VERSION, feature_version=FEATURE_VERSION,
        cost_model_version=COST_MODEL_VERSION, date_range={'from': str(start), 'to': str(end)},
        universe_settings=universe, portfolio_settings=portfolio, cost_settings=vars(costs),
        cost_sources=SOURCES,
        return_basis='PRICE', risk_free_rate_annual=0.0, sortino_minimum_acceptable_return=0.0,
        turnover_definition='ANNUALIZED_TWO_WAY_TRADED_NOTIONAL_OVER_NAV',
        random_seed=7, readiness=readiness, parameters_selected_on_test=False)
    root = config.data_dir / 'artifacts/backtests/factor_v1'
    path = save_backtest(root, config=run_config, metrics=metrics, result=result, ic=ic, deciles=deciles,
                          rolling=rolling, evidence=evidence, extra=stress)
    write_json(path / 'benchmarks.json', baselines)
    write_json(path / 'IC-confidence-interval.json', uncertainty)
    write_json(path / 'ranking-top30.json', scores[scores.as_of == scores.as_of.max()].head(30).to_dict('records'))
    for window in walk_forward(prices, scores, labels, sessions, portfolio=portfolio, cost_model=costs,
            windows=rolling_windows(first_test_year=max(2016, start.year), last_test_year=end.year)):
        curve = window['result'].equity_curve
        if curve.empty:
            continue
        market_window = index_returns(benchmark_frame, curve.trade_date)
        measured, rolling_window = performance_metrics(curve, market_window, window['result'].trades)
        ic_window, deciles_window, summary = diagnostics(window['scores'], labels)
        measured.update(summary)
        save_backtest(path / 'walk_forward' / str(window['window']['test_start'].year),
            config=dict(**run_config, walk_forward_window=window['window'], training_labels=window['train_labels'],
                        embargo_sessions=window['embargo_sessions']), metrics=measured, result=window['result'],
            ic=ic_window, deciles=deciles_window, rolling=rolling_window,
            evidence={'status':'WINDOW_ONLY_NOT_INDEPENDENT_VALIDATION','checks':{}})
    return path, evidence


def main():
    from quant.pipeline.cli import parser_config
    parser, config = parser_config(__doc__)
    parser.add_argument('--estimate-historical-costs', action='store_true')
    parser.add_argument('--skip-robustness', action='store_true', help='Exploratory run only; cannot pass the cost-stress hurdle')
    args = parser.parse_args()
    try:
        path, evidence = run_research(args.config(config), args.start, args.end,
            estimate_historical_costs=args.estimate_historical_costs, full_robustness=not args.skip_robustness)
    except (ValueError, OSError) as error:
        write_json(args.config(config).data_dir / 'reports' / f'backtest-blocked-{args.end}.json',
            dict(status='BLOCKED', date_range={'from':str(args.start),'to':str(args.end)}, reason=str(error),
                 public_recommendations_allowed=False, ML_authorized=False,
                 estimate_historical_costs=args.estimate_historical_costs))
        print(f'Research run blocked: {error}')
        return 1
    print(json.dumps({'artifacts': str(path), 'evidence': evidence['status']}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
