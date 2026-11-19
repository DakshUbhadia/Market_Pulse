"""Controlled V1/V2 comparisons through the shared accounting engine."""
from dataclasses import replace
import numpy as np
import pandas as pd

from quant.backtest.engine import run_backtest
from quant.backtest.metrics import performance_metrics, diagnostics
from quant.backtest.benchmarks import index_returns,total_return_index_returns
from quant.backtest.costs import CostModel
from quant.backtest.portfolio import PortfolioConfig


def compare_models(prices, scores, labels, benchmark, sessions, window, *, cost_model=None,
                   portfolio=None, execution=None, return_basis='PRICE', risk_features=None, risk_policy=None):
    costs=cost_model or CostModel()
    portfolio=portfolio or PortfolioConfig()
    execution=execution or {}
    if return_basis not in ('PRICE','TOTAL_RETURN'):
        raise ValueError('Unknown research return basis')
    required={'full_v1','matched_v1','factor_v2'}
    if not required.issubset(scores):
        raise ValueError('All three controlled comparison arms are required')
    keys=['as_of','instrument_id']
    left,right=[set(map(tuple,scores[name][keys].to_numpy())) for name in ('matched_v1','factor_v2')]
    if left!=right:
        raise ValueError('V1 and V2 must have identical dated covered universes')
    from quant.portfolio.constraints import RiskPolicy
    from quant.portfolio.target import risk_target_builder
    policy = risk_policy or RiskPolicy()
    if risk_features is None:
        raise ValueError('Four-arm comparison requires dated risk/ADV features')
    output={}
    arms = dict(scores, risk_budgeted_v2=scores['factor_v2'])
    for name,ranked in arms.items():
        risk = name == 'risk_budgeted_v2'
        callback, budgets = risk_target_builder(prices, risk_features, sessions, policy) if risk else (None, [])
        arm_execution = dict(execution, target_builder=callback, target_builder_context=risk)
        result=run_backtest(prices,ranked,sessions,start=window['from'],end=window['to'],
            portfolio=portfolio,cost_model=costs,**arm_execution)
        market=(index_returns(benchmark,result.equity_curve.trade_date) if return_basis=='PRICE'
                else total_return_index_returns(benchmark,result.equity_curve.trade_date,sessions))
        metrics,rolling=performance_metrics(result.equity_curve,market,result.trades)
        test=ranked[ranked.as_of.between(pd.Timestamp(window['from']),pd.Timestamp(window['to']))]
        ic,deciles,summary=diagnostics(test,labels)
        means=deciles.groupby('decile').excess_return.mean() if not deciles.empty else pd.Series(dtype=float)
        summary['decile_monotonicity']=float(means.index.to_series().corr(means.rank())) if len(means)==10 else None
        summary['D10_D1_spread']=float(means.iloc[-1]-means.iloc[0]) if len(means)==10 else None
        stress={}
        for multiplier in (1.5,2.):
            stress_callback, _ = risk_target_builder(prices, risk_features, sessions, policy) if risk else (None, [])
            stressed=run_backtest(prices,ranked,sessions,start=window['from'],end=window['to'],
                portfolio=portfolio,cost_model=replace(costs,cost_multiplier=multiplier),
                **dict(execution, target_builder=stress_callback, target_builder_context=risk))
            stress[str(multiplier)]=performance_metrics(stressed.equity_curve,market,stressed.trades)[0]
        from quant.research.risk_evidence import risk_evidence
        from quant.risk.clusters import rebalance_cluster_diagnostics
        _, exposure = rebalance_cluster_diagnostics(prices, ranked, sessions, result.holdings, result.equity_curve)
        risk_report = risk_evidence(result, risk_features, budgets, policy, portfolio.initial_cash, market)
        risk_report['realized_max_cluster_weight'] = float(exposure.max_cluster_weight.max()) if len(exposure) else None
        risk_report['realized_cluster_assessment'] = 'ASSESSED' if len(exposure) and exposure.assessed.all() else 'UNASSESSED'
        output[name]=dict(result=result,metrics=dict(metrics,**summary),ic=ic,deciles=deciles,
                          rolling=rolling,stress=stress, risk_budgets=budgets,
                          risk_evidence=risk_report)
    factor_ic=[]
    v2=scores['factor_v2']
    from quant.models.factor_v2 import BLOCKS
    for block in BLOCKS:
        ranked=v2.copy()
        ranked['raw_score']=ranked[block+'_score']
        ic,_,summary=diagnostics(ranked[ranked.as_of.between(pd.Timestamp(window['from']),pd.Timestamp(window['to']))],labels)
        if not ic.empty:
            ic['block']=block
            factor_ic.append(ic)
    return output,pd.concat(factor_ic,ignore_index=True) if factor_ic else pd.DataFrame()


def v2_decision(windows, criteria):
    # Every declared outer window must pass; never select the best window.
    checks=[]
    for compared in windows:
        v1,v2=[compared[n]['metrics'] for n in ('matched_v1','factor_v2')]
        def finite(*values):
            return all(v is not None and np.isfinite(v) for v in values)
        row=dict(adequate_oos=v2['observations']>=criteria['min_oos_sessions'],
            minimum_ic=finite(v2.get('mean_IC')) and v2['mean_IC'] >= criteria['min_mean_ic'],
            minimum_ir=finite(v2.get('information_ratio')) and v2['information_ratio'] >= criteria['min_ir'],
            mature_labels=(v2.get('label_coverage') or 0)>=criteria['min_label_coverage'],
            ic_improves=finite(v1.get('mean_IC'),v2.get('mean_IC')) and v2['mean_IC']-v1['mean_IC']>=criteria['min_mean_ic_improvement'],
            ir_improves=finite(v1.get('information_ratio'),v2.get('information_ratio')) and v2['information_ratio']-v1['information_ratio']>=criteria['min_ir_improvement'],
            sharpe_preserved=finite(v1.get('Sharpe'),v2.get('Sharpe')) and v2['Sharpe']>=v1['Sharpe'],
            drawdown_preserved=v2['max_drawdown']>=v1['max_drawdown']-criteria['max_drawdown_deterioration'],
            turnover_acceptable=v2['turnover']<=criteria['max_turnover']
                and v2['turnover']-v1['turnover'] <= criteria['max_turnover_increase'],
            positive_net_excess=v2['annualized_excess_return']>0,
            survives_cost_stress=sum(r['annualized_excess_return'] > 0 for r in compared['factor_v2']['stress'].values())
                / len(compared['factor_v2']['stress']) >= criteria['min_robustness_survival'])
        checks.append(row)
    valid = sum(c['adequate_oos'] and c['mature_labels'] for c in checks)
    sufficient = valid >= criteria['min_valid_windows'] and valid == len(checks)
    passed=sufficient and all(all(c.values()) for c in checks)
    decision = ('BLOCKED' if not windows else 'INCONCLUSIVE' if not sufficient else
                'GO_FURTHER_V2_RESEARCH' if passed else 'NO_GO_V2')
    return dict(decision=decision, valid_windows=valid,
        risk_budget_capacity_passed=bool(windows) and all(w.get('risk_budgeted_v2', {}).get('risk_evidence', {}).get('capacity_violations') == 0 for w in windows),
        window_checks=checks,production_validated=False,automatic_model_activation=False,
        elastic_net_research_gate_passed=passed,elastic_net_weight=0.)
