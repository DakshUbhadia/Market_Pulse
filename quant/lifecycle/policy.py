"""Frozen baseline and explicitly labelled research sensitivity scenarios."""
from quant.version import LIFECYCLE_POLICY_VERSION

DEFAULT_LIFECYCLE_SCENARIO = 'MANDATORY_ECONOMIC_EVENTS_ONLY'
SCENARIOS = (DEFAULT_LIFECYCLE_SCENARIO, 'MANDATORY_ONLY', 'KNOWN_EVENT_NEXT_OPEN_EXIT',
             'FORMAL_EXIT_OFFER_PARTICIPATION', 'ZERO_RECOVERY_STRESS')


def resolve_lifecycle_events(lifecycle=None, lifecycle_events=None):
    """Accept the documented keyword while retaining existing callers."""
    if lifecycle is not None and lifecycle_events is not None:
        raise ValueError('Supply lifecycle or lifecycle_events, not both')
    return lifecycle if lifecycle is not None else lifecycle_events
