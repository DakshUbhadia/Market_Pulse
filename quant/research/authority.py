"""Research authority is independent from runtime completion or metric values."""
import json
from pathlib import Path

from quant.governance.gates import GovernanceBlocked

RESEARCH = 'RESEARCH'
DIAGNOSTIC_ONLY = 'DIAGNOSTIC_ONLY'
OUTCOMES = {'BLOCKED_BY_DATA', 'BLOCKED_BY_GOVERNANCE', 'BLOCKED_BY_SOFTWARE',
            'BLOCKED_BY_SOURCE', 'INCONCLUSIVE', 'NO_GO', 'PASS'}


def blocked_outcome(error):
    if isinstance(error, GovernanceBlocked):
        return error.outcome
    from quant.lifecycle.state import UnvaluedHolding
    if isinstance(error, UnvaluedHolding):
        return 'BLOCKED_BY_DATA'
    from quant.data.nse_client import NseSourceError
    if isinstance(error, NseSourceError) or any(t in str(error).upper() for t in ('HTTP 403', 'HTTP 429', 'TIMED OUT', 'CONNECTION')):
        return 'BLOCKED_BY_SOURCE'
    if any(t in str(error).upper() for t in ('UNIT CI', 'JUNIT', 'IMPLEMENTATION SHA', 'COMPILE')):
        return 'BLOCKED_BY_SOFTWARE'
    if isinstance(error, (FileNotFoundError, KeyError)) or any(t in str(error).upper() for t in
            ('NOT_READY', 'LIFECYCLE', 'SHARE', 'COVERAGE', 'MISSING', 'RESEARCH INPUTS', 'MANIFEST')):
        return 'BLOCKED_BY_DATA'
    return 'BLOCKED_BY_SOFTWARE'


def reject_diagnostic_artifacts(root):
    root = Path(root)
    for parent in (root, *root.parents):
        if (parent/'diagnostic-authority.json').is_file() or (parent/'diagnostic-completion.json').is_file():
            raise ValueError('DIAGNOSTIC_ONLY artifacts are ineligible for research seals, registration and promotion')
    config = root/'config.json'
    if config.is_file():
        value = json.loads(config.read_text(encoding='utf-8'))
        if value.get('research_authority') == DIAGNOSTIC_ONLY or value.get('seal_eligible') is False:
            raise ValueError('DIAGNOSTIC_ONLY artifacts cannot authorize research')
