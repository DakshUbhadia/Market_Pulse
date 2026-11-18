"""Conservative corporate-action parsing. Uncertain economics require review."""
import re
import json

import pandas as pd

from quant.data.normalization import record_id, records
from quant.data.security_history import instrument_id, resolve_identity

PATH = '/api/corporates-corporateActions'
COLUMNS = ['event_id', 'instrument_id', 'symbol', 'action_type', 'subject', 'announcement_date',
           'ex_date', 'record_date', 'payment_date', 'ratio_numerator', 'ratio_denominator',
           'cash_amount', 'parse_status', 'source_url', 'source_sha256', 'fetched_at', 'source_payload',
           'source_instrument_id', 'source_isin', 'identity_resolution', 'identity_evidence_date']


def action_identity_lookup(history):
    groups = {} if history is None or history.empty else dict(tuple(history.groupby(['symbol','series'],observed=True)))
    def lookup(symbol, day):
        group = groups.get((symbol,'EQ'))
        if group is None:
            return set()
        day = pd.Timestamp(day)
        return set(group.loc[group.identity_status.eq('RESOLVED') & group.valid_from.le(day)
                             & group.valid_to.ge(day),'instrument_id'].dropna())
    lookup.isins = {} if history is None or history.empty or 'isin' not in history else {
        key:set(group['isin'].dropna()) for key,group in history.groupby('instrument_id',observed=True)}
    return lookup


def reconcile_action_identities(frame, history=None, *, lookup=None):
    """The API sometimes supplies a pre-split ISIN years after its retirement.

    Only a unique identity observed both before and on the action date can
    correct that stale field. A transition on the event date is not bridged.
    Raw payload/source identity are retained, never replaced with today's master.
    """
    result = frame.copy()
    if 'source_instrument_id' not in result:
        result['source_instrument_id'] = result.instrument_id
    for column in ('instrument_id','source_instrument_id','identity_resolution'):
        result[column] = result.get(column,pd.Series(None,index=result.index,dtype=object)).astype(object)
    result['identity_evidence_date'] = pd.to_datetime(result.get('identity_evidence_date',
        pd.Series(pd.NaT,index=result.index)))
    lookup = lookup or action_identity_lookup(history)
    result['source_isin'] = result.get('source_isin',pd.Series(None,index=result.index,dtype=object)).astype(object)
    for i,row in result.iterrows():
        source = row.get('source_instrument_id')
        source = source if isinstance(source,str) else None
        source_isin = row.get('source_isin')
        if not isinstance(source_isin,str):
            payload = row.get('source_payload')
            source_isin = json.loads(payload).get('isin') if isinstance(payload,str) else None
        if not isinstance(source_isin,str):
            candidates = getattr(lookup,'isins',{}).get(source,set())
            source_isin = next(iter(candidates)) if len(candidates) == 1 else None
        day = pd.Timestamp(row.ex_date)
        current, prior = lookup(row.symbol,day), lookup(row.symbol,day-pd.Timedelta(days=1))
        identity, status, evidence = source, 'SOURCE_ISIN_ONLY', pd.NaT
        if len(current) > 1:
            identity, status = None, 'AMBIGUOUS_DATED_IDENTITY'
        elif len(current) == 1:
            observed = next(iter(current))
            if source is None:
                identity, status, evidence = observed, 'DATED_IDENTITY', day
            elif source == observed:
                status, evidence = 'SOURCE_MATCHES_DATED_IDENTITY', day
            elif (prior == current and isinstance(source_isin,str)
                  and len(getattr(lookup,'isins',{}).get(observed,set())) == 1
                  and source_isin[:9] == next(iter(lookup.isins[observed]))[:9]):
                identity, status, evidence = observed, 'STALE_SOURCE_ISIN_RECONCILED', day
            else:
                status = 'IDENTITY_TRANSITION_UNASSESSED' if prior != current else 'SOURCE_IDENTITY_CONFLICT_UNASSESSED'
        result.loc[i,'instrument_id'] = identity
        result.loc[i,'source_instrument_id'] = source
        result.loc[i,'source_isin'] = source_isin
        result.loc[i,'identity_resolution'] = status
        result.loc[i,'identity_evidence_date'] = evidence
    return result


def parse_subject(subject):
    text = ' '.join(subject.lower().split())
    action = ('DEMERGER' if 'demerger' in text or 'de-merger' in text else
              'MERGER' if 'merger' in text or 'amalgamation' in text else
              'SYMBOL_CHANGE' if 'symbol' in text and 'chang' in text else
              'SPLIT' if 'split' in text or 'sub-division' in text or 'sub division' in text else
              'BONUS' if 'bonus' in text else 'RIGHTS' if 'rights' in text else
              'DIVIDEND' if 'dividend' in text else 'OTHER')
    numerator = denominator = cash = None
    status = 'NEEDS_REVIEW'
    # Composite records need explicit component allocation; never guess.
    composite = (sum(word in text for word in ('bonus', 'dividend', 'rights')) > 1
                 or (action == 'SPLIT' and any(word in text for word in ('bonus', 'dividend', 'rights'))))
    if action == 'SPLIT':
        match = re.search(r'from\s+(?:rs\.?|inr|re\.?)?\s*([\d.]+).*?to\s+(?:rs\.?|inr|re\.?)?\s*([\d.]+)', text)
        if match:
            numerator, denominator = map(float, match.groups())  # Old/new face value = shares multiplier.
    elif action in ('BONUS', 'RIGHTS'):
        match = re.search(r'(\d+(?:\.\d+)?)\s*:\s*(\d+(?:\.\d+)?)', text)
        if match:
            numerator, denominator = map(float, match.groups())
    elif action == 'DIVIDEND':
        amounts = re.findall(r'(?:rs\.?|inr|re\.?)\s*([\d]+(?:\.\d+)?)\s*(?:/-)?\s*(?:per share|per equity share)', text)
        if len(amounts) == 1:
            cash = float(amounts[0])
    if action in ('SPLIT', 'BONUS') and numerator and denominator and not composite:
        status = 'PARSED'
    if action == 'DIVIDEND' and cash is not None and cash >= 0 and not composite:
        status = 'PARSED'
    if action == 'OTHER' and text in ('annual general meeting', 'extraordinary general meeting', 'extra ordinary general meeting'):
        status = 'NON_ADJUSTING'
    return dict(action_type=action, ratio_numerator=numerator, ratio_denominator=denominator,
                cash_amount=cash, parse_status=status)


def parse_corporate_actions(payload, raw, history=None):
    rows = []
    for record in records(payload):
        symbol, subject = record.get('symbol'), record.get('subject')
        if not symbol or not isinstance(subject, str) or not record.get('exDate'):
            raise ValueError('Corporate action schema changed')
        ex_date = pd.to_datetime(record['exDate'], format='mixed', errors='raise').normalize()
        identity = instrument_id(record.get('isin'))
        if not identity and history is not None:
            identity = resolve_identity(history, symbol, ex_date)
        row = dict(event_id=record_id(record), instrument_id=identity, symbol=symbol,
                   source_instrument_id=instrument_id(record.get('isin')), source_isin=record.get('isin'),
                   subject=subject, ex_date=ex_date, **parse_subject(subject))
        for name, field in [('announcement_date', 'caBroadcastDate'), ('record_date', 'recDate'),
                            ('payment_date', 'paymentDate')]:
            value = record.get(field)
            row[name] = pd.to_datetime(value, format='mixed') if value and value != '-' else pd.NaT
        row.update(source_url=raw.source_url, source_sha256=raw.sha256, fetched_at=raw.fetched_at,
                   source_payload=json.dumps(record, sort_keys=True))
        rows.append(row)
    frame = pd.DataFrame(rows, columns=COLUMNS).drop_duplicates('event_id')
    return reconcile_action_identities(frame,history) if not frame.empty else frame
