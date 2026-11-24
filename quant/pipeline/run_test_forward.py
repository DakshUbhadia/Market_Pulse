"""Execute controlled forward-engine dry runs in an isolated TEST_ONLY namespace."""
from dataclasses import asdict
from pathlib import Path
import re

from quant.backtest.portfolio import PortfolioConfig
from quant.backtest.costs import CostModel
from quant.forward.signal_store import append_record, content_hash, freeze_signals
from quant.forward.shadow_portfolio import update_shadow
from quant.forward.outcome_tracker import track_outcomes
from quant.forward.metrics import forward_metrics
from quant.governance.gates import GateRegistry, GATE_ID
from quant.identity.transitions import TRANSITION_VERSION
from quant.storage.research_store import git_commit


def run_test_forward(config, *, cohort, prices, benchmark, tri, sessions, scores, as_of,
                     generated_at, next_open, source_manifest, diagnostic_subject_sha256,
                     portfolio=None, costs=None, **execution):
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,63}', cohort):
        raise ValueError('A named TEST_ONLY cohort is required')
    if not re.fullmatch('[0-9a-f]{64}', diagnostic_subject_sha256):
        raise ValueError('Test cohorts require a fixed diagnostic subject digest')
    root = config.data_dir/'forward/test-only'/cohort
    gates = GateRegistry(config.data_dir).require('TEST_FORWARD')
    portfolio, costs = portfolio or PortfolioConfig(), costs or CostModel()
    metadata = dict(cohort_type='TEST_ONLY', real_forward_evidence=False, promotion_eligible=False,
        diagnostic_subject_sha256=diagnostic_subject_sha256, governance_block=GATE_ID)
    append_record(root/'test-cohort.json', dict(metadata, sha256=content_hash(metadata)))
    settings = dict(metadata, portfolio=asdict(portfolio), costs=asdict(costs),
        return_basis='TOTAL_RETURN', security_transition_version=TRANSITION_VERSION,
        lifecycle_scenario=execution.get('lifecycle_scenario', 'MANDATORY_ECONOMIC_EVENTS_ONLY'))
    manifest_hash = content_hash(source_manifest)
    append_record(root/'sources'/f'{manifest_hash}.json', source_manifest)
    freeze_signals(root, scores, as_of=as_of, data_as_of=as_of, generated_at=generated_at,
        git_commit=git_commit(), source_manifest_hash=manifest_hash, next_open=next_open,
        settings=settings, cohort_type='TEST_ONLY')
    update_shadow(root, prices, sessions, as_of=as_of, portfolio=portfolio, cost_model=costs, **execution)
    outcomes = track_outcomes(root, prices, benchmark, tri, sessions, as_of=as_of, cost_model=costs, **execution)
    report = dict(status='TEST_ONLY', root=str(root), **metadata,
        governance_status=gates['human_review_status'], outcomes=outcomes, metrics=forward_metrics(root))
    from quant.storage.research_store import write_json
    write_json(root/'reports/test-forward.json', report)
    return report
