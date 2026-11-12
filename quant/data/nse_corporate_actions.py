"""Conservative corporate-action parsing. Uncertain economics require review."""
import re
import json

import pandas as pd

from quant.data.normalization import record_id, records
from quant.data.security_history import instrument_id, resolve_identity

PATH = '/api/corporates-corporateActions'
COLUMNS = ['event_id', 'instrument_id', 'symbol', 'action_type', 'subject', 'announcement_date',
           'ex_date', 'record_date', 'payment_date', 'ratio_numerator', 'ratio_denominator',
           'cash_amount', 'parse_status', 'source_url', 'source_sha256', 'fetched_at', 'source_payload']


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
                   subject=subject, ex_date=ex_date, **parse_subject(subject))
        for name, field in [('announcement_date', 'caBroadcastDate'), ('record_date', 'recDate'),
                            ('payment_date', 'paymentDate')]:
            value = record.get(field)
            row[name] = pd.to_datetime(value, format='mixed') if value and value != '-' else pd.NaT
        row.update(source_url=raw.source_url, source_sha256=raw.sha256, fetched_at=raw.fetched_at,
                   source_payload=json.dumps(record, sort_keys=True))
        rows.append(row)
    return pd.DataFrame(rows, columns=COLUMNS).drop_duplicates('event_id')
