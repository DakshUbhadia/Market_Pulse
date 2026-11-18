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
                   portfolio=None, execution=None, return_basis='PRICE'):
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
    output={}
    for name,ranked in scores.items():
        result=run_backtest(prices,ranked,sessions,start=window['from'],end=window['to'],
            portfolio=portfolio,cost_model=costs,**execution)
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
            stressed=run_backtest(prices,ranked,sessions,start=window['from'],end=window['to'],
                portfolio=portfolio,cost_model=replace(costs,cost_multiplier=multiplier),**execution)
            stress[str(multiplier)]=performance_metrics(stressed.equity_curve,market,stressed.trades)[0]
        output[name]=dict(result=result,metrics=dict(metrics,**summary),ic=ic,deciles=deciles,
                          rolling=rolling,stress=stress)
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
            mature_labels=(v2.get('label_coverage') or 0)>=criteria['min_label_coverage'],
            ic_improves=finite(v1.get('mean_IC'),v2.get('mean_IC')) and v2['mean_IC']-v1['mean_IC']>=criteria['min_mean_ic_improvement'],
            ir_improves=finite(v1.get('information_ratio'),v2.get('information_ratio')) and v2['information_ratio']-v1['information_ratio']>=criteria['min_ir_improvement'],
            sharpe_preserved=finite(v1.get('Sharpe'),v2.get('Sharpe')) and v2['Sharpe']>=v1['Sharpe'],
            drawdown_preserved=v2['max_drawdown']>=v1['max_drawdown']-criteria['max_drawdown_deterioration'],
            turnover_acceptable=v2['turnover']<=criteria['max_turnover'],
            positive_net_excess=v2['annualized_excess_return']>0,
            survives_cost_stress=compared['factor_v2']['stress']['1.5']['annualized_excess_return']>0)
        checks.append(row)
    passed=bool(checks) and all(all(c.values()) for c in checks)
    return dict(decision='GO_FURTHER_V2_RESEARCH' if passed else 'NO_GO_INVESTIGATE',
        window_checks=checks,production_validated=False,automatic_model_activation=False,
        elastic_net_research_gate_passed=passed,elastic_net_weight=0.)
