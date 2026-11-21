"""Exclusive immutable JSON records; repeat identical writes are idempotent."""
from quant.identity.transitions import TRANSITION_VERSION
import hashlib
import json
import os
from pathlib import Path
import tempfile

import numpy as np
import pandas as pd

from quant.models.factor_v1 import WEIGHTS
from quant.storage.research_store import clean_json
from quant.version import (MODEL_VERSION, FEATURE_VERSION, PORTFOLIO_ACCOUNTING_VERSION,
                           EVIDENCE_POLICY_VERSION, LIFECYCLE_POLICY_VERSION, COST_MODEL_VERSION)


def content_hash(value):
    return hashlib.sha256(json.dumps(clean_json(value), sort_keys=True, separators=(',', ':'),
                                    allow_nan=False).encode()).hexdigest()


def append_record(path, record):
    """Publish a complete file atomically without replacing a previous record."""
    path = Path(path)
    value = clean_json(record)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(value, sort_keys=True, indent=2, allow_nan=False).encode()
    handle, temporary = tempfile.mkstemp(dir=path.parent, suffix='.pending')
    try:
        with os.fdopen(handle, 'wb') as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        try:
            os.link(temporary, path)
        except FileExistsError:
            if json.loads(path.read_text(encoding='utf-8')) != value:
                raise ValueError(f'Immutable forward record already exists: {path.name}') from None
    finally:
        Path(temporary).unlink(missing_ok=True)
    return path


def freeze_signals(root, scores, *, as_of, generated_at, data_as_of, git_commit,
                   source_manifest_hash, next_open, settings, validation_level='FORWARD_PAPER_ONLY',
                   next_session_evidence=None, model_card=None, cohort_type='REAL'):
    if cohort_type not in ('REAL', 'TEST_ONLY'):
        raise ValueError('Unknown forward cohort type')
    if cohort_type == 'REAL':
        from quant.governance.gates import GateRegistry, data_root_for
        GateRegistry(data_root_for(root)).require('V1_FORWARD')
    settings = dict(settings, cohort_type=cohort_type, real_forward_evidence=cohort_type == 'REAL')
    if cohort_type == 'TEST_ONLY':
        settings['promotion_eligible'] = False
        validation_level = 'TEST_ONLY'
    model_version, feature_version = MODEL_VERSION, FEATURE_VERSION
    weights = WEIGHTS
    model_name = 'Factor V1'
    if model_card is not None:
        from quant.models.model_card import verify_model_card
        from quant.version import FACTOR_V2_VERSION, FUNDAMENTAL_FEATURE_VERSION
        from quant.models.factor_v2 import BLOCKS
        verify_model_card(model_card)
        model_version, feature_version = model_card['model_version'], model_card['feature_version']
        if (model_version, feature_version) not in ((MODEL_VERSION, FEATURE_VERSION), (FACTOR_V2_VERSION, FUNDAMENTAL_FEATURE_VERSION)):
            raise ValueError('Unsupported registered forward model versions')
        if settings.get('model_card_sha256') != model_card['sha256']:
            raise ValueError('Registered cohort settings must bind the immutable model card')
        if model_version == FACTOR_V2_VERSION:
            weights = {block: 1/len(BLOCKS) for block in BLOCKS}
            model_name = 'Factor V2 challenger'
    day = pd.Timestamp(as_of).normalize()
    generated = pd.Timestamp(generated_at)
    opening = pd.Timestamp(next_open)
    if generated.tzinfo is None or opening.tzinfo is None:
        raise ValueError('Forward timing requires explicit timezones')
    close = pd.Timestamp(f'{day.date()} 15:30', tz='Asia/Kolkata')
    if not close <= generated < opening or opening <= close:
        raise ValueError('Forward signals must be frozen after signal close and before the next open')
    if pd.Timestamp(data_as_of).date() != day.date():
        raise ValueError('Forward data_as_of must match the signal session')
    if not git_commit or len(source_manifest_hash) != 64:
        raise ValueError('Forward signals require code and source provenance')
    if scores.empty or not pd.to_datetime(scores.as_of).eq(day).all() or scores.instrument_id.duplicated().any():
        raise ValueError('Expected one complete, unique cross section for the signal date')
    if (set(scores['rank']) != set(range(1, len(scores)+1)) or not scores.universe_size.eq(len(scores)).all()
            or not scores.model_version.eq(model_version).all() or not scores.feature_version.eq(feature_version).all()):
        raise ValueError('Forward rankings must use the complete frozen V1 cross section')
    records = []
    for row in scores.sort_values('rank').to_dict('records'):
        contributions = {name: float(row[name+'_score'])*weight for name, weight in weights.items()}
        if (not row.get('eligible',False) or not row.get('feature_valid',False)
                or not np.isfinite([row['raw_score'], row['percentile_score'], row['vol_63'], *contributions.values()]).all()
                or row['vol_63'] <= 0 or not np.isclose(sum(contributions.values()), row['raw_score'])):
            raise ValueError('Invalid forward score, risk or factor contributions')
        key = dict(as_of=str(day.date()), instrument_id=row['instrument_id'], model_version=model_version)
        records.append(dict(**key, signal_id=content_hash(key), symbol=row['symbol'],
            model_name=model_name, feature_version=feature_version,
            security_transition_version=TRANSITION_VERSION,portfolio_accounting_version=PORTFOLIO_ACCOUNTING_VERSION,
            evidence_policy_version=EVIDENCE_POLICY_VERSION, lifecycle_policy_version=LIFECYCLE_POLICY_VERSION,
            score=row['raw_score'], rank=int(row['rank']), universe_size=len(scores),
            factor_contributions=contributions, percentile_score=row['percentile_score'], vol_63=row['vol_63'],
            data_as_of=str(day.date()), generated_at=generated.isoformat(), git_commit=git_commit,
            source_manifest_hash=source_manifest_hash, validation_level=validation_level))
        records[-1].update(cohort_type=cohort_type, real_forward_evidence=cohort_type == 'REAL')
        if cohort_type == 'TEST_ONLY':
            records[-1]['promotion_eligible'] = False
        if model_card is not None and 'adv60' in row:
            records[-1]['adv60'] = float(row['adv60'])
    batch = dict(as_of=str(day.date()), settings=clean_json(settings), signals=records,
                 cohort_type=cohort_type, real_forward_evidence=cohort_type == 'REAL',
                 next_session_open=opening.isoformat(),next_session_evidence=next_session_evidence)
    versions = dict(model_version=model_version,feature_version=feature_version,
        security_transition_version=TRANSITION_VERSION,portfolio_accounting_version=PORTFOLIO_ACCOUNTING_VERSION,cost_model_version=COST_MODEL_VERSION,
        evidence_policy_version=EVIDENCE_POLICY_VERSION,lifecycle_policy_version=LIFECYCLE_POLICY_VERSION)
    existing, _ = read_signals(root)
    for previous in existing:
        if previous['settings'] != batch['settings'] or any(
                any(signal.get(key) != value for key,value in versions.items() if key != 'cost_model_version')
                for signal in previous['signals']):
            raise ValueError('Cohort policy changed; start a new named cohort before appending signals')
    # Exclusive publication is also the admission lock for concurrent writers
    # attempting different policies. It happens before any new signal is stored.
    policy = dict(versions=versions,settings=batch['settings'], cohort_type=cohort_type,
                  real_forward_evidence=cohort_type == 'REAL')
    policy['sha256'] = content_hash(policy)
    append_record(Path(root)/'cohort.json',policy)
    batch['sha256'] = content_hash(batch)
    path = Path(root)/'signals'/f'{day.date()}.json'
    append_record(path, batch)
    return path


def read_signals(root):
    batches, rows = [], []
    policy_path = Path(root)/'cohort.json'
    policy = json.loads(policy_path.read_text(encoding='utf-8')) if policy_path.exists() else None
    if policy is not None and content_hash({k:v for k,v in policy.items() if k != 'sha256'}) != policy.get('sha256'):
        raise ValueError('Immutable cohort policy checksum changed')
    for path in sorted((Path(root)/'signals').glob('*.json')):
        batch = json.loads(path.read_text(encoding='utf-8'))
        if content_hash({k:v for k,v in batch.items() if k != 'sha256'}) != batch['sha256']:
            raise ValueError(f'Forward batch checksum changed: {path.name}')
        kind = batch.get('cohort_type', 'REAL')
        if (kind not in ('REAL', 'TEST_ONLY') or batch['settings'].get('cohort_type', 'REAL') != kind
                or batch['settings'].get('real_forward_evidence', kind == 'REAL') is not (kind == 'REAL')
                or batch.get('real_forward_evidence', kind == 'REAL') is not (kind == 'REAL')
                or (policy is not None and (policy.get('cohort_type', 'REAL') != kind
                    or policy.get('real_forward_evidence', kind == 'REAL') is not (kind == 'REAL')))
                or any(r.get('cohort_type', 'REAL') != kind
                    or r.get('real_forward_evidence', kind == 'REAL') is not (kind == 'REAL')
                    or (kind == 'TEST_ONLY' and r.get('promotion_eligible') is not False)
                    for r in batch['signals'])):
            raise ValueError('TEST_ONLY and real forward evidence cannot be mixed')
        if any(content_hash({k:row[k] for k in ('as_of','instrument_id','model_version')}) != row['signal_id']
               for row in batch['signals']):
            raise ValueError('Forward signal identity changed')
        if policy is not None and (batch['settings'] != policy['settings'] or any(
                any(signal.get(key) != value for key,value in policy['versions'].items() if key != 'cost_model_version')
                for signal in batch['signals'])):
            raise ValueError('Frozen signals differ from the immutable cohort policy')
        batches.append(batch)
        rows.extend(batch['signals'])
    frame = pd.DataFrame(rows)
    if not frame.empty:
        if frame.signal_id.duplicated().any():
            raise ValueError('Duplicate immutable forward signal')
        frame['as_of'] = pd.to_datetime(frame.as_of)
        frame['raw_score'] = frame.score
    return batches, frame
