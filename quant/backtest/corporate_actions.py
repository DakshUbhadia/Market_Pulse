"""Ex-date dividend entitlement on positions held at the preceding close.

Gross cash is credited before ex-date open orders, without automatic reinvestment
or withholding tax. This is an explicit research convention, not payment-date
cash forecasting. Quantities use split-adjusted units; cash per raw share must
be scaled by the ex-date split factor, including subsequent splits in the anchor.
"""
import numpy as np
import pandas as pd

DIVIDEND_CONVENTION = 'GROSS_EX_DATE_CASH_PRIOR_CLOSE_HOLDINGS_NO_AUTOMATIC_REINVESTMENT'


def dividend_events(actions):
    if actions is None or actions.empty:
        return {}
    rows = actions[actions.action_type.eq('DIVIDEND')].drop_duplicates('event_id').copy()
    rows['ex_date'] = pd.to_datetime(rows.ex_date).dt.normalize()
    if rows.instrument_id.isna().any():
        # Unresolved actions are handled by the universe exclusion gate. Do not
        # guess an identity by symbol or credit an unrelated company.
        rows = rows[rows.instrument_id.notna()]
    return {pd.Timestamp(day): group for day, group in rows.groupby('ex_date')}


def dividend_credits(events, positions, bars, day):
    records = []
    for identity, group in events.groupby('instrument_id'):
        quantity = positions.get(identity, 0)
        if quantity <= 0:
            continue
        if len(group) != 1 or not group.parse_status.eq('PARSED').all():
            raise ValueError(f'Unverified dividend entitlement for held identity {identity}')
        event = group.iloc[0]
        bar = bars.get(identity, {})
        factor = bar.get('split_factor')
        if factor is None and bar.get('raw_close', 0) > 0:
            factor = bar['adjusted_close']/bar['raw_close']
        cash = event.cash_amount
        if factor is None or pd.isna(cash) or not np.isfinite([factor,cash]).all() or factor <= 0 or cash < 0:
            raise ValueError(f'Invalid dividend share basis for {identity}')
        records.append(dict(trade_date=day, event_id=event.event_id, instrument_id=identity,
            quantity=quantity, dividend_per_share=float(cash), split_factor=float(factor),
            cash_credit=quantity*factor*cash, convention=DIVIDEND_CONVENTION))
    return records
