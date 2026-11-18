"""Causal adapter for the shared next-open simulator's opt-in risk context."""
import numpy as np
import pandas as pd

from quant.backtest.portfolio import target_portfolio
from quant.portfolio.covariance import shrinkage_covariance
from quant.portfolio.risk_budget import allocate_risk
from quant.risk.clusters import return_clusters


def risk_target_builder(prices, features, sessions, policy, *, lookback=252, min_observations=220):
    reports=[]
    def target(scores,positions,config,*,signal_date,nav,previous_bars):
        selected=target_portfolio(scores,positions,config)
        names=sorted(set(selected.index)|set(positions))
        if not names:
            return pd.Series(dtype=float)
        old={}
        for name,quantity in positions.items():
            mark=previous_bars.get(name,{}).get('adjusted_close')
            if mark is None or not np.isfinite(mark) or mark<=0:
                raise ValueError('Risk budget requires a known prior-close holding mark')
            old[name]=quantity*mark/nav
        # Prices and liquidity are cut off before covariance/cluster construction.
        dates=pd.DatetimeIndex(pd.to_datetime(sessions))
        dates=dates[dates<=signal_date][-(lookback+1):]
        history=prices[prices.instrument_id.isin(names) & pd.to_datetime(prices.trade_date).isin(dates)].copy()
        history.loc[history.adjustment_status.ne('OK'),'adjusted_close']=np.nan
        panel=history.pivot(index='trade_date',columns='instrument_id',values='adjusted_close').reindex(dates)
        covariance,diagnostics=shrinkage_covariance(panel.pct_change(fill_method=None).iloc[1:],signal_date,
            lookback=lookback,min_observations=min_observations)
        universe=features[features.as_of.eq(signal_date)].set_index('instrument_id')
        if not universe.index.is_unique:
            raise ValueError('Ambiguous dated ADV inputs')
        clusters=return_clusters(prices,sessions,signal_date,instrument_ids=names,lookback=lookback,
            min_observations=min_observations).set_index('instrument_id').cluster_id
        weights,report=allocate_risk(covariance,pd.Series(old,dtype=float),universe.adv60,clusters,
                                    nav=nav,selected=selected.index,policy=policy)
        desired = selected.reindex(weights.index).fillna(0.)
        reports.append(dict(as_of=str(signal_date),covariance=diagnostics,**report,
            risk_limited_target_weight=float((desired-weights).clip(lower=0).sum())))
        return weights
    return target,reports
