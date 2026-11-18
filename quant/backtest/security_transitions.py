"""Mandatory one-successor entitlements in split-adjusted research units.

Pending raw units are valued only with an observed successor close. Missing
valuation still blocks; listing expectations never manufacture a quote.
"""
import pandas as pd
from quant.lifecycle.state import share_factor, UnvaluedHolding
from quant.identity.transitions import validate_transitions


class SecurityTransitions:
    def __init__(self, events=None, data_dir=None):
        self.events = validate_transitions(events, data_dir)
        self.processed, self.locks, self.lineages, self.origins = set(), {}, {}, {}
        self.records = []

    def apply(self, day, opening, positions, basis, today, previous):
        events = self.events
        due = events[events.verification_status.eq('VERIFIED_COMPLETE') & events.announced_at.lt(opening)
            & events.ex_date.le(day) & events.effective_date.le(day)]
        for event in due.to_dict('records'):
            key, old, new = event['transition_id'],event['predecessor_instrument_id'],event['successor_instrument_id']
            if key in self.processed:
                continue
            # Mark non-held events too: later purchases cannot earn retroactive entitlements.
            self.processed.add(key)
            if old not in positions:
                continue
            if any(lock['until'] > day for lock in self.locks.get(old, [])):
                raise ValueError('Chained pending transition requires allocation review')
            if old not in previous or new not in today:
                raise UnvaluedHolding(old,day)
            old_quantity = positions.pop(old)
            total_basis = old_quantity*basis.pop(old)
            raw_units = old_quantity*share_factor(previous[old])*event['raw_share_multiplier']
            quantity = raw_units/share_factor(today[new])
            existing = positions.get(new,0.)
            if existing and self.origins.get(new,new) != self.origins.get(old,old):
                raise ValueError('Merging distinct recommendation lots requires allocation review')
            basis[new] = (total_basis+existing*basis.get(new,0.))/(quantity+existing)
            positions[new] = existing+quantity
            self.lineages[new] = event['security_lineage_id']
            self.origins[new] = self.origins.get(old,old)
            self.locks.setdefault(new,[]).append(dict(units=quantity,until=event['first_tradable_date']))
            self.records.append(dict(trade_date=day,transition_id=key,predecessor_instrument_id=old,
                successor_instrument_id=new,security_lineage_id=event['security_lineage_id'],
                recommendation_instrument_id=self.origins[new],raw_share_entitlement=raw_units,
                economic_units=quantity,tradable_units=quantity if day >= event['first_tradable_date'] else 0.,
                pending_units=quantity if day < event['first_tradable_date'] else 0.,transferred_cost_basis=total_basis,tradable_from=event['first_tradable_date']))

    def entry_allowed(self, identity, day, opening):
        rows=self.events
        retired=rows[rows.verification_status.eq('VERIFIED_COMPLETE')
            & rows.predecessor_instrument_id.eq(identity) & rows.successor_instrument_id.ne(identity)
            & rows.ex_date.le(day) & rows.announced_at.lt(opening)]
        return retired.empty

    def pending(self, identity, day):
        return sum(lock['units'] for lock in self.locks.get(identity,[]) if day < lock['until'])
