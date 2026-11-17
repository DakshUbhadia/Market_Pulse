"""Append-only experiment ledger, including blocked and failed attempts."""
import csv
import io
import json
from datetime import datetime, timezone
from uuid import uuid4

from quant.data.http import atomic_write
from quant.storage.research_store import clean_json, git_commit, write_json, digest_file
from quant.version import MODEL_VERSION, FEATURE_VERSION, COST_MODEL_VERSION, EVIDENCE_POLICY_VERSION
from quant.pipeline.state import state_lock

FIELDS = ['experiment_id', 'git_commit', 'model_version', 'feature_version', 'hypothesis',
          'parameters', 'date_run', 'result_summary', 'decision']


def begin_experiment(config, hypothesis, parameters):
    from quant.backtest.report import BASELINE_DIAGNOSTIC_RULE
    from quant.lifecycle.policy import LIFECYCLE_POLICY_VERSION
    from quant.models.factor_v1 import WEIGHTS
    from quant.backtest.portfolio import PortfolioConfig
    from quant.universe.config import UniverseConfig
    from quant.backtest.costs import CostModel
    from quant.config import REPO_ROOT
    costs = CostModel(allow_estimated_history=parameters.get('estimate_historical_costs',False))
    code = {str(path.relative_to(REPO_ROOT)):digest_file(path) for path in (REPO_ROOT/'quant').rglob('*.py')
            if not any(part in ('.venv','tests','__pycache__') for part in path.parts)}
    identifier = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S') + '-' + uuid4().hex[:8]
    record = dict(experiment_id=identifier, git_commit=git_commit(), model_version=MODEL_VERSION,
        feature_version=FEATURE_VERSION, hypothesis=hypothesis,
        parameters=clean_json(dict(parameters, factor_weights=WEIGHTS,
            portfolio=PortfolioConfig(), universe=UniverseConfig(), cost_model_version=COST_MODEL_VERSION,
            cost_settings=vars(costs), cost_schedule=costs.schedule_table(), source_code_sha256=code,
            evidence_policy_version=EVIDENCE_POLICY_VERSION,lifecycle_policy_version=LIFECYCLE_POLICY_VERSION,
            baseline_comparison_policy=BASELINE_DIAGNOSTIC_RULE)),
        date_run=datetime.now(timezone.utc).isoformat(), result_summary='STARTED', decision='PENDING')
    path = config.data_dir / 'research/experiments' / identifier
    path.mkdir(parents=True, exist_ok=False)
    write_json(path / 'frozen-baseline.json', record)
    append_experiment(config, record)
    return record, path


def append_experiment(config, record):
    path = config.data_dir / 'research/experiments.csv'
    with state_lock(path.with_suffix('.lock')):
        previous = path.read_text(encoding='utf-8') if path.exists() else ''
        stream = io.StringIO(newline='')
        writer = csv.DictWriter(stream, fieldnames=FIELDS)
        if not previous:
            writer.writeheader()
        writer.writerow({key: json.dumps(record[key], sort_keys=True) if isinstance(record[key], dict)
                         else record[key] for key in FIELDS})
        atomic_write(path, (previous + stream.getvalue()).encode('utf-8'))
