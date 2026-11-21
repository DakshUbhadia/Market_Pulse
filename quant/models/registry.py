"""Local append-only champion/challenger lifecycle with evidence-gated promotion."""
from datetime import datetime, timezone
from pathlib import Path
import json
import pandas as pd

from quant.backtest.artifacts import verify_backtest_seal
from quant.forward.signal_store import append_record, content_hash
from quant.models.model_card import make_model_card, verify_model_card
from quant.pipeline.state import state_lock
from quant.storage.research_store import digest_file

STATES = {'DRAFT', 'RESEARCH_CANDIDATE', 'HISTORICALLY_VALIDATED', 'FORWARD_CHALLENGER',
          'FORWARD_CHAMPION', 'REJECTED', 'RETIRED'}
TRANSITIONS = {
    'DRAFT': {'RESEARCH_CANDIDATE', 'REJECTED', 'RETIRED'},
    'RESEARCH_CANDIDATE': {'HISTORICALLY_VALIDATED', 'REJECTED', 'RETIRED'},
    'HISTORICALLY_VALIDATED': {'FORWARD_CHALLENGER', 'RETIRED', 'REJECTED'},
    'FORWARD_CHALLENGER': {'FORWARD_CHAMPION', 'REJECTED', 'RETIRED'},
    'FORWARD_CHAMPION': {'RETIRED'}, 'REJECTED': {'RETIRED'}, 'RETIRED': set(),
}


class ModelRegistry:
    def __init__(self, root):
        self.root = Path(root)

    def snapshot(self):
        result, previous = {}, None
        for index, path in enumerate(sorted((self.root/'events').glob('*.json'))):
            row = json.loads(path.read_text(encoding='utf-8'))
            if (row.get('sequence') != index or row.get('previous_sha256') != previous
                    or row.get('sha256') != content_hash({k: v for k, v in row.items() if k != 'sha256'})):
                raise ValueError('Registry journal checksum or sequence changed')
            model = row['model_id']
            card = self.card(model)
            prior = result.get(model, {}).get('state')
            if row['card_sha256'] != card['sha256'] or row['from_state'] != prior:
                raise ValueError('Registry journal differs from immutable model card or prior state')
            if row['state'] not in ({'DRAFT'} if prior is None else TRANSITIONS[prior]):
                raise ValueError('Invalid registry state transition')
            result[model] = row
            previous = row['sha256']
        if sum(r['state'] == 'FORWARD_CHAMPION' for r in result.values()) > 1:
            raise ValueError('Registry contains multiple champions')
        return result

    def card(self, model_id):
        import re
        if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,95}', model_id):
            raise ValueError('Invalid model ID')
        return verify_model_card(json.loads((self.root/'cards'/f'{model_id}.json').read_text(encoding='utf-8')))

    def _append(self, card, state, prior, *, reason, evidence=None, reviewer=None):
        paths = sorted((self.root/'events').glob('*.json'))
        previous = json.loads(paths[-1].read_text(encoding='utf-8'))['sha256'] if paths else None
        record = dict(sequence=len(paths), model_id=card['model_id'], card_sha256=card['sha256'],
            from_state=prior, state=state, previous_sha256=previous, reason=reason,
            evidence=evidence or {}, reviewed_by=reviewer, recorded_at=datetime.now(timezone.utc).isoformat())
        record['sha256'] = content_hash(record)
        append_record(self.root/'events'/f'{len(paths):08d}.json', record)
        return record

    def register(self, value):
        if value.get('research_authority') == 'DIAGNOSTIC_ONLY' or value.get('promotion_eligible') is False:
            raise ValueError('Diagnostic candidates cannot enter the model registry')
        if value.get('historical_experiment'):
            from quant.research.authority import reject_diagnostic_artifacts
            reject_diagnostic_artifacts(value['historical_experiment'])
        card = make_model_card(value)
        with state_lock(self.root/'registry.lock'):
            snapshot = self.snapshot()
            if card['model_id'] in snapshot:
                raise ValueError('Model ID already registered; use a new version/ID')
            append_record(self.root/'cards'/f'{card["model_id"]}.json', card)
            return self._append(card, 'DRAFT', None, reason='Registered immutable candidate')

    def _historical_evidence(self, card):
        if card['decision'] != 'PASS':
            raise ValueError('Historical decision PASS is required')
        root = Path(card['historical_experiment'])
        verify_backtest_seal(root)
        if digest_file(root/'completion.json') != card['historical_completion_sha256']:
            raise ValueError('Historical completion seal differs from model card')
        config = json.loads((root/'config.json').read_text(encoding='utf-8'))
        if config.get('git_commit') != card['git_commit']:
            raise ValueError('Historical code differs from model card')
        is_v2 = (root/'v2-decision.json').is_file()
        decision = json.loads((root/('v2-decision.json' if is_v2 else 'v1-decision.json')).read_text(encoding='utf-8'))
        expected = 'GO_FURTHER_V2_RESEARCH' if is_v2 else 'GO_FURTHER_V1_RESEARCH'
        if decision.get('decision') != expected:
            raise ValueError('Sealed historical evidence does not pass its research gate')
        if content_hash(config.get('manifest', {k: config[k] for k in ('files',) if k in config})) != card['data_manifest_hash']:
            raise ValueError('Historical input manifest differs from model card')
        if is_v2 and content_hash(config['specification']) != card['spec_hash']:
            raise ValueError('Historical specification differs from model card')
        windows = config['specification'].get('evaluation_windows', []) if is_v2 else [config.get('date_range', {})]
        interval = {'from':windows[0].get('from'), 'to':windows[-1].get('to')} if windows else None
        if not interval or not all(interval.values()) or card['test_window'] not in (interval, windows):
            raise ValueError('Historical evaluation interval differs from model card')
        if not is_v2:
            specification = root/'specification.json'
            if not specification.is_file() or content_hash(json.loads(specification.read_text(encoding='utf-8'))) != card['spec_hash']:
                raise ValueError('Historical V1 frozen specification differs from model card')
        if is_v2 and any(config['specification'].get(k) != card[k] for k in (
                'model_version', 'feature_version', 'cost_model_version', 'risk_policy_version', 'coverage_policy')):
            raise ValueError('Historical model policies differ from model card')
        if not is_v2 and (config.get('model_version') != card['model_version']
                         or config.get('feature_version') != card['feature_version']):
            raise ValueError('Historical V1 versions differ from model card')
        return dict(historical_experiment=str(root), completion_sha256=card['historical_completion_sha256'])

    def transition(self, model_id, state, *, reason, reviewer=None, forward_root=None,
                   monitoring_report=None, manual_record=None, incident_root=None):
        if state not in STATES or not str(reason).strip():
            raise ValueError('A valid model state and reason are required')
        with state_lock(self.root/'registry.lock'):
            snapshot = self.snapshot()
            prior = snapshot[model_id]['state']
            if state not in TRANSITIONS[prior]:
                raise ValueError(f'Forbidden model transition: {prior} -> {state}')
            card = self.card(model_id)
            evidence = {}
            if state in ('HISTORICALLY_VALIDATED', 'FORWARD_CHALLENGER', 'FORWARD_CHAMPION'):
                evidence.update(self._historical_evidence(card))
                from quant.governance.gates import GateRegistry, data_root_for
                GateRegistry(data_root_for(self.root)).require('V1_MODEL_REGISTRATION' if
                    str(card['model_version']).startswith('factor_v1') else 'V2_PROMOTION')
            if state == 'FORWARD_CHAMPION':
                if incident_root is None:
                    raise ValueError('Champion promotion requires manual review and an assessed incident ledger')
                from quant.monitoring.incidents import IncidentLedger
                incident_report = IncidentLedger(incident_root).report(model_id=model_id, cohort_root=forward_root)
                if incident_report['unresolved_incidents'] != 0:
                    raise ValueError('Champion promotion requires zero unresolved incidents')
                if any(r['state'] == state for r in snapshot.values()):
                    raise ValueError('Retire the existing champion before promoting another')
                if not reviewer or not manual_record or not forward_root or not monitoring_report:
                    raise ValueError('Champion promotion requires manual review and independent forward/monitoring evidence')
                from quant.forward.metrics import forward_metrics
                from quant.forward.signal_store import read_signals
                batches, _ = read_signals(forward_root)
                if any(b.get('cohort_type', 'REAL') == 'TEST_ONLY' for b in batches):
                    raise ValueError('TEST_ONLY cohorts cannot authorize model promotion')
                if not batches or any(b['settings'].get('model_card_sha256') != card['sha256'] for b in batches):
                    raise ValueError('Forward cohort is not bound to this immutable model card')
                metrics = forward_metrics(forward_root)
                policy = card.get('forward_policy', {})
                # Policy is frozen at registration; missing policy cannot promote.
                if (policy.get('min_signal_sessions', 0) < 126 or policy.get('min_rebalance_cycles', 0) < 6
                        or policy.get('min_matured_63_signals', 0) < 30
                        or metrics['signal_sessions'] < policy['min_signal_sessions']
                        or metrics['rebalance_cycles'] < policy['min_rebalance_cycles']
                        or metrics['outcomes']['63']['distinct_signals'] < policy['min_matured_63_signals']):
                    raise ValueError('Insufficient independent forward sample under the frozen policy')
                monitor = json.loads(Path(monitoring_report).read_text(encoding='utf-8'))
                if monitor.get('incident_ledger') != incident_report:
                    raise ValueError('Monitoring incident ledger is missing or stale')
                cohort_hash = content_hash([b['sha256'] for b in batches])
                if (monitor.get('status') != 'PASS' or monitor.get('model_card_sha256') != card['sha256']
                        or monitor.get('cohort_root') != str(Path(forward_root).resolve())
                        or monitor.get('cohort_evidence_sha256') != cohort_hash
                        or monitor.get('as_of') != max(b['as_of'] for b in batches)
                        or monitor.get('unresolved_incidents') != 0 or not monitor.get('operational_integrity')):
                    raise ValueError('Unresolved accounting/data incidents or unassessed operational integrity')
                manual = json.loads(Path(manual_record).read_text(encoding='utf-8'))
                if (manual.get('model_id') != model_id or manual.get('reviewed_by') != reviewer
                        or manual.get('model_card_sha256') != card['sha256']
                        or manual.get('monitoring_sha256') != digest_file(monitoring_report)
                        or manual.get('decision') != 'PROMOTE' or not manual.get('reason') or not manual.get('reviewed_at')):
                    raise ValueError('Manual promotion record does not authorize this candidate')
                reviewed = pd.Timestamp(manual['reviewed_at'])
                if reviewed.tzinfo is None or reviewed > pd.Timestamp.now(tz='UTC'):
                    raise ValueError('Manual promotion review requires a past timezone-aware timestamp')
                from quant.governance.review import require_review
                require_review(manual, review_type='MODEL_PROMOTION', subject_sha256=card['sha256'], decision='PROMOTE')
                if manual['reviewer_name'] != reviewer:
                    raise ValueError('Promotion human reviewer differs from the attributed registry reviewer')
                append_record(self.root/'governance'/f'{manual["sha256"]}.json', manual)
                evidence.update(forward_metrics=metrics, monitoring_sha256=digest_file(monitoring_report),
                                incident_ledger_sha256=incident_report['ledger_sha256'],
                                manual_record_sha256=digest_file(manual_record))
            return self._append(card, state, prior, reason=reason, evidence=evidence, reviewer=reviewer)

    def require_forward_candidate(self, model_id):
        row = self.snapshot().get(model_id, {})
        if row.get('state') not in ('FORWARD_CHALLENGER', 'FORWARD_CHAMPION'):
            raise ValueError('Model registry does not permit forward collection')
        card = self.card(model_id)
        self._historical_evidence(card)
        return card
