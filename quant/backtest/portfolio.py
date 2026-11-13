from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class PortfolioConfig:
    holdings: int = 25
    entry_percentile: float = 90
    exit_percentile: float = 35
    max_weight: float = .05
    initial_cash: float = 1_000_000

    def __post_init__(self):
        if not (self.holdings > 0 and 0 < self.max_weight <= 1 and self.initial_cash > 0
                and 0 <= self.exit_percentile <= self.entry_percentile <= 100):
            raise ValueError('Invalid portfolio configuration')


def capped_inverse_volatility(volatility, cap=.05):
    if not np.isfinite(volatility).all() or (volatility <= 0).any():
        raise ValueError('Inverse-volatility sizing requires positive finite risk estimates')
    if not 0 < cap <= 1:
        raise ValueError('Position cap must be in (0, 1]')
    weights = pd.Series(0.0, index=volatility.index)
    remaining = set(volatility.index)
    budget = min(1.0, len(volatility)*cap)
    while remaining and budget > 1e-12:
        inverse = 1/volatility.loc[sorted(remaining)]
        proposed = inverse/inverse.sum()*budget
        bound = proposed[proposed > cap].index
        if not len(bound):
            weights.loc[proposed.index] = proposed
            break
        weights.loc[bound] = cap
        budget -= cap*len(bound)
        remaining.difference_update(bound)
    return weights


def target_portfolio(scores, current, config=None):
    config = config or PortfolioConfig()
    rows = scores.dropna(subset=['instrument_id', 'vol_63', 'percentile_score'])
    rows = rows[rows.vol_63 > 0].set_index('instrument_id', drop=False)
    rows.index.name = None
    if not rows.index.is_unique:
        raise ValueError('Duplicate ranking identities')
    retained = rows[rows.index.isin(current) & (rows.percentile_score >= config.exit_percentile)]
    retained = retained.sort_values(['raw_score', 'instrument_id'], ascending=[False, True]).head(config.holdings)
    entrants = rows[(rows.percentile_score > config.entry_percentile) & ~rows.index.isin(retained.index)]
    entrants = entrants.sort_values(['raw_score', 'instrument_id'], ascending=[False, True]).head(config.holdings - len(retained))
    selected = pd.concat([retained, entrants])
    return capped_inverse_volatility(selected.vol_63, config.max_weight) if len(selected) else pd.Series(dtype=float)
