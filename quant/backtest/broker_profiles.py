"""Broker assumptions are distinct from statutory/exchange verification."""
from dataclasses import dataclass
import math


@dataclass(frozen=True)
class BrokerProfile:
    name: str
    brokerage_rate: float = 0.
    dp_sell: float = 13.
    verification_status: str = 'BROKER_ASSUMPTION'

    def __post_init__(self):
        if not all(math.isfinite(value) and value >= 0 for value in (self.brokerage_rate,self.dp_sell)):
            raise ValueError('Invalid broker charge assumption')


def resolve_broker_profile(name):
    if name != 'GENERIC_ZERO_DELIVERY':
        raise ValueError('Unsupported broker profile; DHAN/ZERODHA/ANGEL require sourced schedules; CUSTOM requires explicit rates')
    return BrokerProfile(name)
