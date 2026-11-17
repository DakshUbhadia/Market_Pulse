"""Gated, reproducible V1 research and rolling OOS evaluation; no publishing."""
import json
from datetime import date

import pandas as pd

from quant.backtest.engine import run_backtest
from quant.backtest.portfolio import PortfolioConfig
from quant.backtest.costs import CostModel, SOURCES
from quant.backtest.benchmarks import index_returns, baseline_target, total_return_index_returns
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
from quant.version import PORTFOLIO_ACCOUNTING_VERSION
from quant.risk.clusters import rebalance_cluster_diagnostics, CLUSTER_VERSION
from quant.storage.duckdb_store import query_dataset
from quant.storage.parquet_store import write_parquet


def run_research(config, start, end, *, estimate_historical_costs=False, full_robustness=True,
                 hypothesis='Frozen untuned Factor V1 baseline', total_return=False):
    from quant.backtest.experiments import begin_experiment, append_experiment
    record, experiment_path = begin_experiment(config, hypothesis, dict(start=str(start), end=str(end),
        estimate_historical_costs=estimate_historical_costs, full_robustness=full_robustness,
        total_return=total_return))
    try:
        path, evidence = _run_research(config, start, end,
            estimate_historical_costs=estimate_historical_costs, full_robustness=full_robustness, total_return=total_return)
    except Exception as error:
        record.update(result_summary=f'{type(error).__name__}: {error}', decision='BLOCKED')
        write_json(experiment_path / 'outcome.json', record)
        append_experiment(config, record)
        raise
    record.update(result_summary=str(path), decision=evidence['status'])
    write_json(experiment_path / 'outcome.json', record)
    append_experiment(config, record)
    return path, evidence


def _run_research(config, start, end, *, estimate_historical_costs=False, full_robustness=True, total_return=False):
    readiness = require_research_ready(config, end, start)
    manifest = input_manifest(config, end)
    prices, benchmark_frame, sessions, delivery, indices = load_research_data(config, end)
    universe, portfolio = UniverseConfig(), PortfolioConfig()
    costs = CostModel(allow_estimated_history=estimate_historical_costs)
    actions, tri = None, None
    if total_return:
        actions = query_dataset(config.data_dir, 'corporate_actions', end=end).drop_duplicates('event_id')
        tri = query_dataset(config.data_dir, 'index_tri', end=end)
    features = build_feature_matrix(prices, benchmark_frame, sessions, universe_config=universe, delivery=delivery, eligible_only=True)
    scores = score_factor_v1(features)
    labels = forward_labels(prices, benchmark_frame, sessions, signal_keys=scores[['as_of','instrument_id']])
    result = run_backtest(prices, scores, sessions, start=start, end=end, portfolio=portfolio, cost_model=costs,
                          corporate_actions=actions)
    market = (total_return_index_returns(tri[tri.index_name.eq('NIFTY 500 TRI')], result.equity_curve.trade_date, sessions)
              if total_return else index_returns(benchmark_frame, result.equity_curve.trade_date))
    metrics, rolling = performance_metrics(result.equity_curve, market, result.trades)
    test_scores = scores[scores.as_of.between(pd.Timestamp(start), pd.Timestamp(end))]
    ic, deciles, ic_summary = diagnostics(test_scores, labels)
    metrics.update(ic_summary)
    uncertainty = block_bootstrap(ic.IC if not ic.empty else [])
    baselines = {}
    for name in ('NIFTY 50', 'NIFTY 500'):
        returns = (total_return_index_returns(tri[tri.index_name.eq(name + ' TRI')], result.equity_curve.trade_date, sessions)
                   if total_return else index_returns(indices[indices.index_name == name], result.equity_curve.trade_date))
        baselines[name] = {'total_return': float((1+returns).prod()-1),
            'basis': 'GROSS_TOTAL_RETURN_INDEX' if total_return else 'GROSS_PRICE_INDEX'}
    for name in ('liquid_equal_weight', 'momentum_12_1_top25', 'inverse_volatility'):
        alternative = run_backtest(prices, features, sessions, start=start, end=end, portfolio=portfolio,
                                   cost_model=costs, target_builder=baseline_target(name), corporate_actions=actions)
        baselines[name], _ = performance_metrics(alternative.equity_curve, market, alternative.trades)
    stress = robustness_runs(prices, scores, market, sessions, start=start, end=end, portfolio=portfolio,
        cost_model=costs, universe_config=universe, benchmark_frame=benchmark_frame, delivery=delivery,
        corporate_actions=actions) if full_robustness else {}
    clusters, exposure = rebalance_cluster_diagnostics(prices, scores, sessions, result.holdings, result.equity_curve)
    assessed = not exposure.empty and exposure.assessed.all()
    evidence = evaluate_evidence(metrics, ic_summary, deciles, stress.get('cost_1_5x', {}).get('metrics', {}),
        result.equity_curve, market, costs_verified=all(costs.schedule(day).verified for day in result.equity_curve.trade_date), baselines=baselines,
        cluster_concentration=float(exposure.max_cluster_weight.max()) if not exposure.empty else None,
        clusters_assessed=assessed, pit_data_verified=readiness['status']=='READY')
    verify_manifest(config, manifest)
    run_config = dict(**manifest, model_version=MODEL_VERSION, feature_version=FEATURE_VERSION,
        cost_model_version=COST_MODEL_VERSION, date_range={'from': str(start), 'to': str(end)},
        universe_settings=universe, portfolio_settings=portfolio, cost_settings=vars(costs),
        cost_sources=SOURCES,
        return_basis='TOTAL_RETURN' if total_return else 'PRICE', label_return_basis='PRICE',
        portfolio_accounting_version=PORTFOLIO_ACCOUNTING_VERSION if total_return else 'price_1.0.0',
        cluster_version=CLUSTER_VERSION,
        risk_free_rate_annual=0.0, sortino_minimum_acceptable_return=0.0,
        turnover_definition='ANNUALIZED_TWO_WAY_TRADED_NOTIONAL_OVER_NAV',
        random_seed=7, readiness=readiness, parameters_selected_on_test=False)
    root = config.data_dir / 'artifacts/backtests/factor_v1'
    path = save_backtest(root, config=run_config, metrics=metrics, result=result, ic=ic, deciles=deciles,
                          rolling=rolling, evidence=evidence, extra=stress)
    write_json(path / 'benchmarks.json', baselines)
    write_json(path / 'cost-schedule.json', costs.schedule_table())
    write_parquet(clusters, path / 'clusters.parquet')
    write_json(path / 'cluster-exposure.json', exposure.to_dict('records'))
    if total_return:
        write_json(path / 'secondary-price-benchmarks.json', {name:float((1+index_returns(
            indices[indices.index_name.eq(name)],result.equity_curve.trade_date)).prod()-1) for name in ('NIFTY 50','NIFTY 500')})
    write_json(path / 'IC-confidence-interval.json', uncertainty)
    write_json(path / 'ranking-top30.json', scores[scores.as_of == scores.as_of.max()].head(30).to_dict('records'))
    for window in walk_forward(prices, scores, labels, sessions, portfolio=portfolio, cost_model=costs,
            windows=rolling_windows(first_test_year=max(2016, start.year), last_test_year=end.year), corporate_actions=actions):
        curve = window['result'].equity_curve
        if curve.empty:
            continue
        market_window = (total_return_index_returns(tri[tri.index_name.eq('NIFTY 500 TRI')],curve.trade_date,sessions)
                         if total_return else index_returns(benchmark_frame, curve.trade_date))
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
    from quant.boundaries import DEFAULT_BACKTEST_START
    parser.set_defaults(start=DEFAULT_BACKTEST_START)
    parser.add_argument('--estimate-historical-costs', action='store_true')
    parser.add_argument('--total-return', action='store_true', help='Gross ex-date cash dividends, evaluated against official TRI')
    parser.add_argument('--hypothesis', default='Frozen untuned Factor V1 baseline')
    parser.add_argument('--skip-robustness', action='store_true', help='Exploratory run only; cannot pass the cost-stress hurdle')
    args = parser.parse_args()
    try:
        path, evidence = run_research(args.config(config), args.start, args.end,
            estimate_historical_costs=args.estimate_historical_costs, full_robustness=not args.skip_robustness,
            total_return=args.total_return, hypothesis=args.hypothesis)
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
