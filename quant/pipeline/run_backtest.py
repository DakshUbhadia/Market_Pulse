"""Gated, reproducible V1 research and rolling OOS evaluation; no publishing."""
from quant.lifecycle.policy import DEFAULT_LIFECYCLE_SCENARIO
from quant.lifecycle.state import UnvaluedHolding
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
from quant.backtest.report import evaluate_evidence, BASELINE_DIAGNOSTIC_RULE, v1_research_decision
from quant.backtest.artifacts import save_backtest, seal_backtest
from quant.features.matrix import build_feature_matrix
from quant.features.labels import forward_labels
from quant.models.factor_v1 import score_factor_v1
from quant.universe.config import UniverseConfig
from quant.pipeline.check_research_ready import require_research_ready
from quant.pipeline.certify_implementation import require_certified_implementation
from quant.storage.research_store import input_manifest, load_research_data, write_json, verify_manifest
from quant.version import MODEL_VERSION, FEATURE_VERSION, COST_MODEL_VERSION
from quant.version import PORTFOLIO_ACCOUNTING_VERSION
from quant.version import EVIDENCE_POLICY_VERSION
from quant.backtest.lifecycle import LIFECYCLE_POLICY_VERSION, SCENARIOS
from quant.pipeline.backfill_lifecycle import load_lifecycle
from quant.risk.clusters import rebalance_cluster_diagnostics, cluster_sensitivity, CLUSTER_VERSION
from quant.storage.duckdb_store import query_dataset
from quant.storage.parquet_store import write_parquet


def run_research(config, start, end, *, estimate_historical_costs=False, full_robustness=True,
                 hypothesis='Frozen untuned Factor V1 baseline', total_return=False, lifecycle_scenario=DEFAULT_LIFECYCLE_SCENARIO,
                 evaluation_window=None):
    window = None
    if evaluation_window is not None:
        from quant.research.evaluation_window import load_evaluation_window
        window = load_evaluation_window(evaluation_window)
        if window['requested_start'] != str(start):
            raise ValueError('Evaluation window must match the originally requested baseline start')
        start = date.fromisoformat(window['effective_start'])
    from quant.backtest.experiments import begin_experiment, append_experiment
    record, experiment_path = begin_experiment(config, hypothesis, dict(start=str(start), end=str(end),
        estimate_historical_costs=estimate_historical_costs, full_robustness=full_robustness,
        total_return=total_return, lifecycle_scenario=lifecycle_scenario, evaluation_window=window))
    try:
        path, evidence = _run_research(config, start, end,
            estimate_historical_costs=estimate_historical_costs, full_robustness=full_robustness, total_return=total_return,
            lifecycle_scenario=lifecycle_scenario,prepared_root=experiment_path, evaluation_window=window)
    except Exception as error:
        record.update(result_summary=f'{type(error).__name__}: {error}', decision='BLOCKED')
        if isinstance(error,UnvaluedHolding):
            record['parameters']['unresolved_held_lifecycle_events'] = 1
            record['parameters']['blocked_holding'] = dict(instrument_id=error.instrument_id,
                trade_date=str(error.trade_date.date()),lifecycle_scenario=lifecycle_scenario)
        write_json(experiment_path / 'outcome.json', record)
        append_experiment(config, record)
        raise
    record.update(result_summary=str(path), decision=evidence['status'])
    write_json(experiment_path / 'outcome.json', record)
    append_experiment(config, record)
    return path, evidence


def _run_research(config, start, end, *, estimate_historical_costs=False, full_robustness=True, total_return=False,
                  lifecycle_scenario=DEFAULT_LIFECYCLE_SCENARIO,prepared_root=None, evaluation_window=None):
    readiness = require_research_ready(config, end, start)
    implementation = require_certified_implementation(config)
    manifest = input_manifest(config, end)
    prices, benchmark_frame, sessions, delivery, indices = load_research_data(config, end)
    lifecycle_events = load_lifecycle(config)
    from quant.identity.transitions import load_transitions, TRANSITION_VERSION
    transitions = load_transitions(config)
    universe, portfolio = UniverseConfig(), PortfolioConfig()
    costs = CostModel(allow_estimated_history=estimate_historical_costs)
    actions, tri = None, None
    if total_return:
        actions = query_dataset(config.data_dir, 'corporate_actions', end=end).drop_duplicates('event_id')
        tri = query_dataset(config.data_dir, 'index_tri', end=end)
    features = build_feature_matrix(prices, benchmark_frame, sessions, universe_config=universe, delivery=delivery, eligible_only=True, lifecycle_events=lifecycle_events)
    scores = score_factor_v1(features)
    labels = forward_labels(prices, benchmark_frame, sessions, signal_keys=scores[['as_of','instrument_id']])
    if prepared_root is not None:
        # A held-event stop must not discard the historical review population.
        # These are input diagnostics, never completed or forward evidence.
        verify_manifest(config,manifest)
        write_parquet(scores[['as_of','instrument_id','symbol','vol_63','rank','percentile_score','raw_score',
            'model_version','feature_version']],prepared_root/'prepared-scores.parquet')
        write_parquet(features[['as_of','instrument_id','symbol','eligible','adv60','history_sessions',
            'lifecycle_status']],prepared_root/'prepared-universe.parquet')
        write_json(prepared_root/'prepared-inputs.json',dict(status='PREPARED_INPUTS_ONLY',manifest=manifest,
            model_version=MODEL_VERSION,feature_version=FEATURE_VERSION,completed_baseline=False,forward_evidence=False))
    result = run_backtest(prices, scores, sessions, start=start, end=end, portfolio=portfolio, cost_model=costs,
                          corporate_actions=actions, lifecycle_events=lifecycle_events, lifecycle_scenario=lifecycle_scenario, security_transitions=transitions, transition_data_dir=config.data_dir)
    from quant.pipeline.audit_lifecycle import audit_lifecycle
    lifecycle_report = audit_lifecycle(config,as_of=end,holdings=result.holdings,
        lifecycle_records=result.lifecycle,scores=scores,portfolio_sessions=result.equity_curve.trade_date,write=False)
    if lifecycle_report['status'] == 'BLOCKED' or lifecycle_report['held_events_unresolved']:
        raise ValueError('Held lifecycle events remain unresolved; baseline cannot be sealed')
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
        benchmark_curve = pd.DataFrame(dict(trade_date=result.equity_curve.trade_date,
            daily_return=returns.to_numpy(),nav=portfolio.initial_cash*(1+returns.to_numpy()).cumprod(),turnover=0.))
        baselines[name],_ = performance_metrics(benchmark_curve,market)
        baselines[name]['basis'] = 'GROSS_TOTAL_RETURN_INDEX' if total_return else 'GROSS_PRICE_INDEX'
    for name in ('liquid_equal_weight', 'momentum_12_1_top25', 'inverse_volatility'):
        alternative = run_backtest(prices, features, sessions, start=start, end=end, portfolio=portfolio,
                                   cost_model=costs, target_builder=baseline_target(name), corporate_actions=actions, lifecycle_events=lifecycle_events, lifecycle_scenario=lifecycle_scenario, security_transitions=transitions, transition_data_dir=config.data_dir)
        baselines[name], _ = performance_metrics(alternative.equity_curve, market, alternative.trades)
    stress = robustness_runs(prices, scores, market, sessions, start=start, end=end, portfolio=portfolio,
        cost_model=costs, universe_config=universe, benchmark_frame=benchmark_frame, delivery=delivery,
        corporate_actions=actions, lifecycle_events=lifecycle_events, lifecycle_scenario=lifecycle_scenario, security_transitions=transitions, transition_data_dir=config.data_dir) if full_robustness else {}
    clusters, exposure = rebalance_cluster_diagnostics(prices, scores, sessions, result.holdings, result.equity_curve)
    assessed = not exposure.empty and exposure.assessed.all()
    evidence = evaluate_evidence(metrics, ic_summary, deciles, stress.get('cost_1_5x', {}).get('metrics', {}),
        result.equity_curve, market, costs_verified=all(costs.schedule(day).verified for day in result.equity_curve.trade_date), baselines=baselines,
        cluster_concentration=float(exposure.max_cluster_weight.max()) if not exposure.empty else None,
        clusters_assessed=assessed, pit_data_verified=readiness['status']=='READY' and readiness.get('lifecycle_data_ready',False))
    verify_manifest(config, manifest)
    run_config = dict(**manifest, implementation_certification=implementation,
        manifest=manifest,
        model_version=MODEL_VERSION, feature_version=FEATURE_VERSION,
        cost_model_version=COST_MODEL_VERSION, date_range={'from': str(start), 'to': str(end)},
        universe_settings=universe, portfolio_settings=portfolio, cost_settings=vars(costs),
        cost_sources=SOURCES,
        return_basis='TOTAL_RETURN' if total_return else 'PRICE', label_return_basis='PRICE',
        portfolio_accounting_version=PORTFOLIO_ACCOUNTING_VERSION if total_return else 'price_1.0.0',
        cluster_version=CLUSTER_VERSION, security_transition_version=TRANSITION_VERSION, lifecycle_policy_version=LIFECYCLE_POLICY_VERSION,
        evidence_policy_version=EVIDENCE_POLICY_VERSION,
        baseline_comparison_policy=BASELINE_DIAGNOSTIC_RULE,
        lifecycle_scenario=lifecycle_scenario, lifecycle_event_count=len(lifecycle_events),
        risk_free_rate_annual=0.0, sortino_minimum_acceptable_return=0.0,
        turnover_definition='ANNUALIZED_TWO_WAY_TRADED_NOTIONAL_OVER_NAV',
        random_seed=7, readiness=readiness, parameters_selected_on_test=False)
    if evaluation_window is not None:
        selection = pd.DatetimeIndex(pd.to_datetime(evaluation_window['selection_calendar']))
        actual = pd.DatetimeIndex(pd.to_datetime(sessions))
        if not selection.equals(actual[(actual >= selection.min()) & (actual <= selection.max())]):
            raise ValueError('Evaluation window calendar differs from the actual research calendar')
        run_config['evaluation_window'] = evaluation_window
    root = config.data_dir / 'artifacts/backtests/factor_v1'
    path = save_backtest(root, config=run_config, metrics=metrics, result=result, ic=ic, deciles=deciles,
                          rolling=rolling, evidence=evidence, extra=stress)
    write_json(path/'input-manifest.json', manifest)
    if prepared_root is not None:
        write_json(path/'specification.json', json.loads((prepared_root/'frozen-baseline.json').read_text(encoding='utf-8')))
    if evaluation_window is not None:
        write_json(path/'evaluation-window.json', evaluation_window)
    write_json(path / 'benchmarks.json', baselines)
    write_json(path / 'baseline-comparison.json',evidence['baseline_comparison'])
    write_json(path / 'v1-decision.json', v1_research_decision(evidence, metrics, baselines))
    write_parquet(pd.DataFrame(evidence['baseline_comparison']),path/'baseline-comparison.parquet')
    write_json(path / 'cost-schedule.json', costs.schedule_table())
    write_parquet(clusters, path / 'clusters.parquet')
    write_json(path / 'cluster-exposure.json', exposure.to_dict('records'))
    sensitivity = cluster_sensitivity(prices,scores,sessions,result.holdings,result.equity_curve)
    write_parquet(sensitivity,path/'cluster-sensitivity.parquet')
    write_json(path/'lifecycle-audit.json',lifecycle_report)
    if total_return:
        write_json(path / 'secondary-price-benchmarks.json', {name:float((1+index_returns(
            indices[indices.index_name.eq(name)],result.equity_curve.trade_date)).prod()-1) for name in ('NIFTY 50','NIFTY 500')})
    write_json(path / 'IC-confidence-interval.json', uncertainty)
    write_json(path / 'ranking-top30.json', scores[scores.as_of == scores.as_of.max()].head(30).to_dict('records'))
    windows = rolling_windows(first_test_year=max(2016, start.year), last_test_year=end.year)
    if evaluation_window is not None:
        for window in windows:
            window['test_start'] = max(start, window['test_start'])
            window['test_end'] = min(end, window['test_end'])
    for window in walk_forward(prices, scores, labels, sessions, portfolio=portfolio, cost_model=costs,
            windows=windows, corporate_actions=actions, lifecycle_events=lifecycle_events, lifecycle_scenario=lifecycle_scenario, security_transitions=transitions, transition_data_dir=config.data_dir):
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
    verify_manifest(config, manifest)
    seal_backtest(path)
    return path, evidence


def main():
    from quant.pipeline.cli import parser_config
    parser, config = parser_config(__doc__)
    from quant.boundaries import DEFAULT_BACKTEST_START
    parser.set_defaults(start=DEFAULT_BACKTEST_START)
    parser.add_argument('--estimate-historical-costs', action='store_true')
    parser.add_argument('--total-return', action='store_true', help='Gross ex-date cash dividends, evaluated against official TRI')
    from pathlib import Path
    parser.add_argument('--evaluation-window', type=Path, help='Immutable evidence-only fallback declaration; preserves original experiments')
    parser.add_argument('--lifecycle-scenario', choices=SCENARIOS, default=DEFAULT_LIFECYCLE_SCENARIO)
    parser.add_argument('--hypothesis', default='Frozen untuned Factor V1 baseline')
    parser.add_argument('--skip-robustness', action='store_true', help='Exploratory run only; cannot pass the cost-stress hurdle')
    args = parser.parse_args()
    try:
        path, evidence = run_research(args.config(config), args.start, args.end,
            estimate_historical_costs=args.estimate_historical_costs, full_robustness=not args.skip_robustness,
            total_return=args.total_return, hypothesis=args.hypothesis, lifecycle_scenario=args.lifecycle_scenario,
            evaluation_window=args.evaluation_window)
    except (ValueError, OSError) as error:
        write_json(args.config(config).data_dir / 'reports' / f'backtest-blocked-{args.end}.json',
            dict(status='BLOCKED', date_range={'from':str(args.start),'to':str(args.end)}, reason=str(error),
                 public_recommendations_allowed=False, ML_authorized=False,
                 lifecycle_scenario=args.lifecycle_scenario,lifecycle_policy_version=LIFECYCLE_POLICY_VERSION,
                 unresolved_held_lifecycle_events=1 if isinstance(error,UnvaluedHolding) else None,
                 estimate_historical_costs=args.estimate_historical_costs))
        print(f'Research run blocked: {error}')
        return 1
    print(json.dumps({'artifacts': str(path), 'evidence': evidence['status']}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
