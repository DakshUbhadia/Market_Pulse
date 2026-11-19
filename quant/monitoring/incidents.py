"""Immutable, hash-chained research incidents with explicit resolution events."""
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4
import json
import re

from quant.forward.signal_store import append_record, content_hash
from quant.pipeline.state import state_lock

INCIDENT_CLASSES = {
    'DATA_CORRECTION', 'SOURCE_OUTAGE', 'PARSER_REGRESSION', 'COVERAGE_DROP',
    'ACCOUNTING_ERROR', 'LIFECYCLE_ERROR', 'TRANSITION_ERROR', 'MODEL_DRIFT', 'RISK_LIMIT_BREACH',
}
SEVERITIES = {'LOW', 'MEDIUM', 'HIGH', 'CRITICAL'}


class IncidentLedger:
    def __init__(self, root):
        self.root = Path(root)

    def initialize(self):
        with state_lock(self.root/'ledger.lock'):
            if not (self.root/'ledger.json').exists():
                append_record(self.root/'ledger.json', dict(version='research_incidents_1.0.0',
                    created_at=datetime.now(timezone.utc).isoformat()))
        return self.snapshot()

    def snapshot(self):
        if not (self.root/'ledger.json').is_file():
            raise ValueError('Incident ledger is uninitialized; absence is not zero incidents')
        states, previous = {}, content_hash(json.loads((self.root/'ledger.json').read_text(encoding='utf-8')))
        for index, path in enumerate(sorted((self.root/'events').glob('*.json'))):
            row = json.loads(path.read_text(encoding='utf-8'))
            body = {k: v for k, v in row.items() if k != 'sha256'}
            if (row.get('sequence') != index or row.get('previous_sha256') != previous
                    or row.get('sha256') != content_hash(body)):
                raise ValueError('Incident journal checksum or sequence changed')
            incident = row['incident']
            key = incident['incident_id']
            prior = states.get(key)
            if prior is None:
                if incident['status'] != 'OPEN':
                    raise ValueError('Incident resolution has no opening event')
            elif (prior['status'] != 'OPEN' or incident['status'] != 'RESOLVED'
                    or any(incident[k] != prior[k] for k in prior if k not in ('status', 'resolution', 'resolved_at'))):
                raise ValueError('Invalid incident transition')
            states[key], previous = incident, row['sha256']
        return dict(incidents=states, sha256=previous)

    def _append(self, incident):
        snapshot = self.snapshot()
        count = len(list((self.root/'events').glob('*.json')))
        row = dict(sequence=count, previous_sha256=snapshot['sha256'], incident=incident)
        row['sha256'] = content_hash(row)
        append_record(self.root/'events'/f'{count:08d}.json', row)
        return incident

    def open(self, incident_class, *, severity, affected_models, affected_cohorts,
             affected_dates, evidence, incident_id=None):
        if incident_class not in INCIDENT_CLASSES or severity not in SEVERITIES or not evidence:
            raise ValueError('Incident requires a supported class, severity and evidence')
        for values in (affected_models, affected_cohorts, affected_dates):
            if not isinstance(values, list) or any(not isinstance(v, str) or not v.strip() for v in values):
                raise ValueError('Incident scopes must be explicit lists; empty means all')
        from datetime import date
        for day in affected_dates:
            date.fromisoformat(day)
        key = incident_id or uuid4().hex
        if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,95}', key):
            raise ValueError('Invalid incident ID')
        self.initialize()
        with state_lock(self.root/'ledger.lock'):
            if key in self.snapshot()['incidents']:
                raise ValueError('Incident ID already exists')
            return self._append(dict(incident_id=key, incident_class=incident_class,
                opened_at=datetime.now(timezone.utc).isoformat(), severity=severity,
                affected_models=sorted(set(affected_models)), affected_cohorts=sorted(set(affected_cohorts)),
                affected_dates=sorted(set(affected_dates)), evidence=evidence,
                status='OPEN', resolution=None, resolved_at=None))

    def resolve(self, incident_id, *, resolution, reviewer, evidence):
        if not str(resolution).strip() or not str(reviewer).strip() or not evidence:
            raise ValueError('Resolution requires a reason, reviewer and evidence')
        with state_lock(self.root/'ledger.lock'):
            prior = self.snapshot()['incidents'][incident_id]
            if prior['status'] != 'OPEN':
                raise ValueError('Incident is already resolved')
            return self._append(dict(prior, status='RESOLVED',
                resolution=dict(reason=resolution, reviewer=reviewer, evidence=evidence),
                resolved_at=datetime.now(timezone.utc).isoformat()))

    def report(self, *, model_id=None, cohort_root=None):
        snapshot = self.snapshot()
        cohort = str(Path(cohort_root).resolve()) if cohort_root else None
        rows = [r for r in snapshot['incidents'].values()
                if (not model_id or not r['affected_models'] or model_id in r['affected_models'])
                and (not cohort or not r['affected_cohorts'] or cohort in r['affected_cohorts'])]
        unresolved = [r for r in rows if r['status'] == 'OPEN']
        mapping = {'ACCOUNTING_ERROR': 'accounting', 'LIFECYCLE_ERROR': 'lifecycle', 'TRANSITION_ERROR': 'transition'}
        counts = dict(data=0, lifecycle=0, transition=0, accounting=0, model=0, risk=0)
        for row in unresolved:
            dimension = mapping.get(row['incident_class'], {'MODEL_DRIFT': 'model', 'RISK_LIMIT_BREACH': 'risk'}.get(row['incident_class'], 'data'))
            counts[dimension] += 1
        return dict(ledger_root=str(self.root.resolve()), ledger_sha256=snapshot['sha256'],
                    unresolved_incidents=len(unresolved), counts=counts, incidents=rows)


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    args = parser.parse_args()
    ledger = IncidentLedger(args.root)
    ledger.initialize()
    print(json.dumps(ledger.report(), indent=2))
