"""Immutable provenance for a candidate; state changes live in the registry journal."""
from datetime import datetime, timezone
import re

from quant.forward.signal_store import content_hash

REQUIRED = {
    'model_id', 'model_version', 'feature_version', 'spec_hash', 'git_commit',
    'data_manifest_hash', 'training_window', 'validation_window', 'test_window',
    'coverage_policy', 'cost_model_version', 'risk_policy_version',
    'historical_metrics', 'decision', 'decision_reason',
}


def validate_model_card(card):
    if not REQUIRED.issubset(card) or any(card.get(k) in (None, '') for k in REQUIRED):
        raise ValueError('Model card is missing required provenance')
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,95}', card['model_id']):
        raise ValueError('Invalid model ID')
    for field in ('spec_hash', 'data_manifest_hash'):
        if not re.fullmatch('[0-9a-f]{64}', card[field]):
            raise ValueError('Model card requires SHA-256 provenance')
    if not re.fullmatch('[0-9a-f]{40}', card['git_commit']):
        raise ValueError('Model card requires a full git commit')
    if card['decision'] not in ('PENDING', 'PASS', 'FAIL'):
        raise ValueError('Unknown historical decision')
    return card


def make_model_card(value):
    card = dict(value)
    card.setdefault('registered_at', datetime.now(timezone.utc).isoformat())
    validate_model_card(card)
    card['sha256'] = content_hash({k: v for k, v in card.items() if k != 'sha256'})
    return card


def verify_model_card(card):
    validate_model_card(card)
    if card.get('sha256') != content_hash({k: v for k, v in card.items() if k != 'sha256'}):
        raise ValueError('Immutable model card checksum changed')
    return card
