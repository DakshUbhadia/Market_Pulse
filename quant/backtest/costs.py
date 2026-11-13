"""Versioned delivery costs. Historical proxies require explicit opt-in.

NSE/FATAX/63809: equity delivery STT .1% each side.
NSE/FA/73061: 297+10 INR/crore before March 2026, 306.99+.01 after.
NSE levy page: uniform .015% buyer stamp duty from July 2020; GST 18%.
Broker baseline: zero delivery brokerage and 13 INR DP before GST per sale.
Pre-October-2024 exchange/broker/state charges are estimates, never certified rates.
"""
import math
import os
from dataclasses import dataclass, field
from datetime import date as Date

from quant.version import COST_MODEL_VERSION

SOURCES = ['https://nsearchives.nseindia.com/content/circulars/FATAX63809.pdf',
           'https://nsearchives.nseindia.com/content/circulars/FA64232.pdf',
           'https://nsearchives.nseindia.com/content/circulars/FA73061.pdf',
           'https://www.nseindia.com/static/invest/first-time-investor-sebi-turnover-fees-stt-other-levies',
           'https://zerodha.com/charges',
           'https://support.zerodha.com/category/account-opening/resident-individual/ri-charges/articles/ipft-charges',
           'https://support.zerodha.com/category/account-opening/resident-individual/ri-charges/articles/what-do-dp-charges-mean']


@dataclass(frozen=True)
class CostSchedule:
    effective_from: Date
    effective_to: Date | None = None  # Exclusive.
    brokerage_rate: float = 0
    stt_rate: float = .001
    exchange_rate: float = .0000297
    ipft_rate: float = .000001
    sebi_rate: float = .000001
    gst_rate: float = .18
    stamp_buy: float = .00015
    stamp_sell: float = 0
    dp_sell: float = 13
    verified: bool = True


@dataclass
class CostModel:
    slippage_bps: float = field(default_factory=lambda: float(os.getenv('QUANT_BASE_SLIPPAGE_BPS', '5')))
    cost_multiplier: float = 1
    slippage_multiplier: float = 1
    allow_estimated_history: bool = False
    schedules: tuple = ()

    def __post_init__(self):
        if not all(math.isfinite(value) and value >= 0 for value in
                   (self.slippage_bps, self.cost_multiplier, self.slippage_multiplier)):
            raise ValueError('Costs must be finite and nonnegative')
        if not self.schedules:
            self.schedules = (CostSchedule(Date(2024, 10, 1), Date(2026, 3, 1)),
                              CostSchedule(Date(2026, 3, 1), exchange_rate=.000030699, ipft_rate=.000000001))
        self.schedules = tuple(sorted(self.schedules, key=lambda row: row.effective_from))
        for i, row in enumerate(self.schedules):
            if row.effective_to is not None and row.effective_to <= row.effective_from:
                raise ValueError('Invalid cost schedule date range')
            if i and (self.schedules[i-1].effective_to is None or self.schedules[i-1].effective_to > row.effective_from):
                raise ValueError('Overlapping cost schedules')
            for key, value in vars(row).items():
                if key not in ('effective_from', 'effective_to', 'verified') and (not math.isfinite(value) or value < 0):
                    raise ValueError(f'Invalid cost rate {key}')

    def schedule(self, day):
        day = Date.fromisoformat(str(day)[:10])
        for row in self.schedules:
            if row.effective_from <= day and (row.effective_to is None or day < row.effective_to):
                return row
        if not self.allow_estimated_history:
            raise ValueError(f'No verified cost schedule for {day}; supply schedules or explicitly allow historical estimates')
        # Deliberately visible stress proxies, not assertions about historical law.
        return CostSchedule(Date(2010, 1, 1), brokerage_rate=.0003, exchange_rate=.0000345,
            ipft_rate=0, sebi_rate=.000002, gst_rate=.18,
            stamp_buy=.0003 if day < Date(2020, 7, 1) else .00015,
            stamp_sell=.0003 if day < Date(2020, 7, 1) else 0, dp_sell=13.5, verified=False)

    def cost(self, *, date, side, product='DELIVERY', turnover):
        if side not in ('BUY', 'SELL') or product != 'DELIVERY':
            raise ValueError('Only BUY/SELL equity DELIVERY is supported')
        if not math.isfinite(turnover) or turnover < 0:
            raise ValueError('Invalid turnover')
        row = self.schedule(date)
        components = dict(brokerage=turnover*row.brokerage_rate, stt=turnover*row.stt_rate,
            exchange=turnover*row.exchange_rate, ipft=turnover*row.ipft_rate, sebi=turnover*row.sebi_rate,
            stamp_duty=turnover*(row.stamp_buy if side == 'BUY' else row.stamp_sell),
            dp_charge=row.dp_sell if side == 'SELL' and turnover > 0 else 0,
            slippage=turnover*self.slippage_bps/10_000*self.slippage_multiplier)
        components['gst'] = row.gst_rate * sum(components[key] for key in ('brokerage', 'exchange', 'ipft', 'sebi', 'dp_charge'))
        components = {key: value*self.cost_multiplier for key, value in components.items()}
        components['total'] = sum(components.values())
        components['schedule_verified'] = row.verified
        components['cost_model_version'] = COST_MODEL_VERSION
        return components
