"""Append matured forward outcomes and update local paper diagnostics."""
from datetime import date
import json

from quant.backtest.costs import CostModel
from quant.forward.outcome_tracker import track_outcomes
from quant.forward.signal_store import read_signals, content_hash
from quant.lifecycle.policy import DEFAULT_LIFECYCLE_SCENARIO
from quant.pipeline.backfill_lifecycle import load_lifecycle
from quant.pipeline.check_research_ready import require_research_ready
from quant.storage.duckdb_store import query_dataset
from quant.storage.research_store import load_research_data, write_json, clean_json
from quant.version import (COST_MODEL_VERSION, MODEL_VERSION, FEATURE_VERSION,
                           PORTFOLIO_ACCOUNTING_VERSION, LIFECYCLE_POLICY_VERSION, EVIDENCE_POLICY_VERSION)


def update_forward_outcomes(config,as_of):
    from quant.pipeline.cli import completed_day
    if as_of > completed_day(config):
        raise ValueError('Forward outcomes cannot use a future or incomplete EOD date')
    require_research_ready(config,as_of)
    root = config.data_dir/'forward/factor_v1'
    batches,signals = read_signals(root)
    if signals.empty:
        raise ValueError('No frozen forward signals; historical backfills are not forward tests')
    costs = CostModel()
    from dataclasses import asdict
    for batch in batches:
        if (batch['settings']['lifecycle_scenario'] != DEFAULT_LIFECYCLE_SCENARIO
                or batch['settings']['cost_model_version'] != COST_MODEL_VERSION
                or batch['settings']['costs'] != clean_json(asdict(costs))):
            raise ValueError('Outcome policies differ from the frozen paper cohort')
        for signal in batch['signals']:
            versions = dict(model_version=MODEL_VERSION,feature_version=FEATURE_VERSION,
                portfolio_accounting_version=PORTFOLIO_ACCOUNTING_VERSION,
                lifecycle_policy_version=LIFECYCLE_POLICY_VERSION,evidence_policy_version=EVIDENCE_POLICY_VERSION)
            if any(signal.get(key) != value for key,value in versions.items()):
                raise ValueError('Outcome versions differ from the immutable signal cohort')
            manifest = json.loads((root/'sources'/f'{signal["source_manifest_hash"]}.json').read_text(encoding='utf-8'))
            if content_hash(manifest) != signal['source_manifest_hash']:
                raise ValueError('Frozen source manifest changed')
    prices,benchmark,sessions,_,_ = load_research_data(config,as_of)
    tri = query_dataset(config.data_dir,'index_tri',end=as_of)
    tri = tri[tri.index_name.eq('NIFTY 500 TRI')]
    actions = query_dataset(config.data_dir,'corporate_actions',end=as_of).drop_duplicates('event_id')
    report = track_outcomes(root,prices,benchmark,tri,sessions,as_of=as_of,cost_model=costs,
        corporate_actions=actions,lifecycle=load_lifecycle(config),lifecycle_scenario=DEFAULT_LIFECYCLE_SCENARIO)
    write_json(config.data_dir/'reports/forward-outcomes.json',report)
    return report


def main():
    from quant.pipeline.cli import parser_config
    parser,config = parser_config(__doc__)
    parser.add_argument('--as-of',type=date.fromisoformat,required=True)
    args = parser.parse_args()
    try:
        result = update_forward_outcomes(args.config(config),args.as_of)
    except (OSError,ValueError,KeyError) as error:
        result = dict(status='BLOCKED',reason=str(error))
        write_json(args.config(config).data_dir/'reports/forward-outcomes.json',result)
    print(json.dumps(result,indent=2))
    return 1 if result.get('status') == 'BLOCKED' or result.get('blocked') else 0


if __name__ == '__main__':
    raise SystemExit(main())
