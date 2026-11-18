"""Explicit long-only portfolio research policy and participation diagnostics."""
from dataclasses import dataclass
import math
import numpy as np


@dataclass(frozen=True)
class RiskPolicy:
    max_weight: float = .05
    max_cluster_weight: float = .25
    adv_fraction: float = .01
    target_volatility: float = .15
    gross_exposure: float = 1.
    turnover_penalty: float = .001

    def __post_init__(self):
        values = (self.max_weight,self.max_cluster_weight,self.adv_fraction,self.target_volatility,self.gross_exposure)
        if any(not math.isfinite(v) or not 0 < v <= 1 for v in values) or not math.isfinite(self.turnover_penalty) or self.turnover_penalty < 0:
            raise ValueError('Invalid risk policy')


def capacity_report(target, previous, adv, nav, *, fraction=.01):
    if not math.isfinite(nav) or nav <= 0 or not 0 < fraction <= 1:
        raise ValueError('Capacity requires explicit positive portfolio capital')
    frame = target.rename('target_weight').to_frame()
    frame['previous_weight'] = previous.reindex(frame.index).fillna(0)
    frame['adv'] = adv.reindex(frame.index)
    if not np.isfinite(frame).all().all() or (frame.adv <= 0).any():
        raise ValueError('Missing or invalid ADV capacity inputs')
    frame['order_value'] = abs(frame.target_weight-frame.previous_weight)*nav
    frame['participation'] = frame.order_value/frame.adv
    frame['capacity_passed'] = frame.participation <= fraction+1e-9
    return frame
