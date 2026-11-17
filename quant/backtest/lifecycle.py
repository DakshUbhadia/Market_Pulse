"""PIT investability and mandatory economics. Offers never imply participation."""
import numpy as np
import pandas as pd

LIFECYCLE_POLICY_VERSION = 'pit_lifecycle_1.0.0'
SCENARIOS = ('KNOWN_EVENT_NEXT_OPEN_EXIT', 'MANDATORY_ONLY')
RISK_TYPES = set('SUSPENSION_ANNOUNCED SUSPENDED DELISTING_ANNOUNCED DELISTED '
    'VOLUNTARY_DELISTING COMPULSORY_DELISTING MERGER_ANNOUNCED MERGER_EFFECTIVE '
    'SHARE_CONVERSION CASH_SETTLEMENT EXIT_OFFER DEMERGER SECURITY_CANCELLED ZERO_RECOVERY DISSEMINATION_BOARD UNKNOWN'.split())
STATES = {'SUSPENSION_ANNOUNCED':'SUSPENSION_ANNOUNCED', 'SUSPENDED':'SUSPENDED',
    'DELISTING_ANNOUNCED':'DELISTING_ANNOUNCED','DELISTED':'DELISTED',
    'VOLUNTARY_DELISTING':'DELISTING_ANNOUNCED','COMPULSORY_DELISTING':'DELISTED',
    'MERGER_ANNOUNCED':'MERGER_PENDING','MERGER_EFFECTIVE':'MERGER_PENDING',
    'CASH_SETTLEMENT':'CASH_SETTLED','SHARE_CONVERSION':'CONVERTED',
    'RELISTING':'RELISTED','SUCCESSOR_LISTING':'ACTIVE','TENDER_OFFER':'TENDER_AVAILABLE',
    'EXIT_OFFER':'TENDER_AVAILABLE'}


def simulation_time(day, clock):
    return pd.Timestamp(f'{pd.Timestamp(day).date()} {clock}', tz='Asia/Kolkata').tz_convert('UTC')


class Lifecycle:
    def __init__(self, events=None, scenario='KNOWN_EVENT_NEXT_OPEN_EXIT'):
        if scenario not in SCENARIOS:
            raise ValueError('Unsupported lifecycle scenario; no undocumented recovery assumptions')
        self.scenario = scenario
        self.events = events.copy() if events is not None else pd.DataFrame()
        if not self.events.empty:
            if self.events.lifecycle_event_id.duplicated().any():
                raise ValueError('Duplicate lifecycle events')
            self.events['announced_at'] = pd.to_datetime(self.events.announced_at, utc=True)
            for key in ('effective_date','settlement_date','last_trading_date'):
                self.events[key] = pd.to_datetime(self.events[key])
            self.events = self.events.sort_values(['announced_at','effective_date','lifecycle_event_id'])
        self.by_identity = {} if self.events.empty else dict(tuple(self.events.groupby('instrument_id')))

    def known(self, identity, timestamp):
        rows = self.by_identity.get(identity)
        if rows is None:
            return pd.DataFrame()
        return rows[rows.verification_status.eq('VERIFIED') & rows.announced_at.le(timestamp)]

    def status(self, identity, timestamp):
        known = self.known(identity, timestamp)
        state, risk, reason, tradable = 'ACTIVE', False, '', True
        day = timestamp.tz_convert('Asia/Kolkata').tz_localize(None).normalize()
        for event in known.itertuples():
            kind = event.event_type
            if kind in ('EXIT_OFFER','TENDER_OFFER') and risk:
                continue  # An optional offer does not restore exchange access.
            if kind in ('RELISTING','SUCCESSOR_LISTING'):
                if event.effective_date <= day:
                    state, risk, reason, tradable = STATES[kind], False, '', True
                continue
            if event.effective_date <= day and kind in ('SUSPENDED','DELISTED','COMPULSORY_DELISTING',
                    'SECURITY_CANCELLED','MERGER_EFFECTIVE','SHARE_CONVERSION','CASH_SETTLEMENT','ZERO_RECOVERY'):
                tradable = False
            if pd.notna(event.last_trading_date) and event.last_trading_date < day:
                tradable = False
            if kind in RISK_TYPES:
                risk, reason = True, kind
            if event.effective_date <= day or kind.endswith('_ANNOUNCED'):
                state = STATES.get(kind, 'UNKNOWN')
            elif kind in RISK_TYPES:
                state = 'SUSPENSION_ANNOUNCED' if 'SUSPEN' in kind else 'DELISTING_ANNOUNCED'
        return dict(lifecycle_status=state, entry_allowed=not risk, lifecycle_reason=reason, trading_allowed=tradable)

    def resolutions(self, identity, timestamp, processed):
        known = self.known(identity, timestamp)
        if known.empty:
            return []
        day = timestamp.tz_convert('Asia/Kolkata').tz_localize(None).normalize()
        rows = []
        for row in known.to_dict('records'):
            if row['lifecycle_event_id'] in processed or not row['mandatory'] or row['optional']:
                continue
            due = row['settlement_date'] if row['event_type'] == 'CASH_SETTLEMENT' else row['effective_date']
            if row['event_type'] in ('CASH_SETTLEMENT','SHARE_CONVERSION','ZERO_RECOVERY') and due == day:
                rows.append(row)
        if len(rows) > 1:
            raise ValueError(f'Conflicting lifecycle resolutions for {identity}')
        return rows


def share_factor(bar):
    factor = bar.get('split_factor')
    if factor is None and bar.get('raw_close', 0) > 0:
        factor = bar['adjusted_close'] / bar['raw_close']
    if factor is None or not np.isfinite(factor) or factor <= 0:
        raise ValueError('Lifecycle settlement requires verified raw-share basis')
    return factor


def overlay_universe(frame, events):
    policy = Lifecycle(events)
    result = frame.copy()
    result['lifecycle_status'], result['entry_allowed'], result['lifecycle_reason'] = 'ACTIVE', True, ''
    result['trading_allowed'] = True
    affected = result.instrument_id.isin(policy.by_identity)
    for index,row in result.loc[affected].iterrows():
        for key,value in policy.status(row.instrument_id, simulation_time(row.as_of,'15:30')).items():
            result.at[index,key] = value
    blocked = ~result.entry_allowed
    result.loc[blocked & result.exclusion_reason.eq(''), 'exclusion_reason'] = 'KNOWN_LIFECYCLE_RISK'
    result['eligible'] &= result.entry_allowed
    return result
