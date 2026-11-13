import math
import os
from dataclasses import dataclass, field


@dataclass(frozen=True)
class UniverseConfig:
    min_history_sessions: int = field(default_factory=lambda: int(os.getenv('QUANT_MIN_HISTORY_SESSIONS', '252')))
    min_trading_presence: float = field(default_factory=lambda: float(os.getenv('QUANT_MIN_TRADING_PRESENCE', '.95')))
    min_adv60: float = field(default_factory=lambda: float(os.getenv('QUANT_MIN_ADV60', '50000000')))
    min_price: float = field(default_factory=lambda: float(os.getenv('QUANT_MIN_PRICE', '0')))

    def __post_init__(self):
        if self.min_history_sessions < 1 or not 0 <= self.min_trading_presence <= 1:
            raise ValueError('Invalid history or trading-presence requirement')
        if not all(math.isfinite(value) and value >= 0 for value in (self.min_adv60, self.min_price)):
            raise ValueError('Liquidity and price thresholds must be finite and nonnegative')
