from datetime import datetime, timezone

import numpy as np
import pandas as pd

from quant.universe.eligible import panels, eligibility
from quant.features.momentum import momentum_features
from quant.features.relative_strength import relative_strength
from quant.features.risk import risk_features
from quant.features.liquidity import liquidity_features
from quant.features.normalize import normalize_cross_section
from quant.version import FEATURE_VERSION

SCORE_FEATURES = ['mom_63', 'mom_126_ex_21', 'mom_252_ex_21', 'distance_52w_high',
    'rs_nifty500_63', 'rs_nifty500_126', 'vol_63', 'beta_252', 'abs_drawdown_252',
    'cvar_95_252', 'log_adv60', 'log_amihud60', 'trading_presence_252']


def build_feature_matrix(prices, benchmark, sessions, *, universe_config=None, delivery=None,
                         as_of=None, medium_lookback=126, long_lookback=252, eligible_only=False):
    prices = prices.copy()
    if as_of is not None:
        prices = prices[pd.to_datetime(prices.trade_date) <= pd.Timestamp(as_of)]
    if delivery is not None and not delivery.empty:
        keys = ['trade_date', 'symbol', 'series']
        if delivery.duplicated(keys).any():
            raise ValueError('Duplicate delivery keys')
        prices = prices.merge(delivery[keys + ['deliverable_percent']], on=keys, how='left', validate='many_to_one')
    benchmark = benchmark.copy()
    benchmark['trade_date'] = pd.to_datetime(benchmark.trade_date)
    if benchmark.trade_date.duplicated().any():
        raise ValueError('Duplicate benchmark sessions')
    market = benchmark.set_index('trade_date').close
    rows = []
    for panel in panels(prices, sessions):
        base = eligibility(panel, universe_config)
        if eligible_only and not base.eligible.any():
            continue
        if eligible_only:
            positions = np.flatnonzero(base.eligible.to_numpy())
            left = max(0, positions[0] - max(252, medium_lookback, long_lookback))
            panel = panel.iloc[left:positions[-1]+1]
            base = base.reindex(panel.index)
        if as_of is not None:
            if panel.index[-1] != pd.Timestamp(as_of):
                continue
            # Snapshot features need at most 252 returns or the configured lag;
            # eligibility above retains the full observed listing history.
            panel = panel.tail(max(253, medium_lookback + 1, long_lookback + 1))
            base = base.reindex(panel.index)
        blocks = [momentum_features(panel.adjusted_close, medium_lookback=medium_lookback, long_lookback=long_lookback),
                  relative_strength(panel.adjusted_close, market), risk_features(panel.adjusted_close, market),
                  liquidity_features(panel)]
        out = pd.concat([base.drop(columns='trading_presence_252')] + blocks, axis=1)
        out['abs_drawdown_252'] = out.max_drawdown_252.abs()
        out['log_adv60'] = np.log(out.adv_60.where(out.adv_60 > 0))
        out['log_amihud60'] = np.log(out.amihud_60.clip(lower=1e-16))
        out['feature_valid'] = np.isfinite(out[SCORE_FEATURES]).all(axis=1) & out.vol_63.gt(0)
        observed = panel.observed & (panel.index == pd.Timestamp(as_of)) if as_of is not None else panel.observed
        if eligible_only:
            observed &= base.eligible
        rows.append(out.loc[observed].reset_index())
    if not rows:
        raise ValueError('No observed prices for feature construction')
    result = pd.concat(rows, ignore_index=True)
    if as_of is not None:
        result = result[result.as_of == pd.Timestamp(as_of)].copy()
    result = normalize_cross_section(result, SCORE_FEATURES)
    result['feature_version'] = FEATURE_VERSION
    result['generated_at'] = datetime.now(timezone.utc).isoformat()
    return result
