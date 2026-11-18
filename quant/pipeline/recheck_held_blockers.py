"""Replay preserved frozen V1 scores to prioritize actual held blockers.

This diagnostic never creates a baseline completion seal or V1 decision. A
successful path requires a separate full research run with all diagnostics.
"""
import json
from pathlib import Path
from datetime import date
from quant.backtest.engine import run_backtest
from quant.backtest.costs import CostModel
from quant.backtest.experiments import begin_experiment, append_experiment
from quant.lifecycle.state import UnvaluedHolding
from quant.identity.transitions import load_transitions
from quant.pipeline.backfill_lifecycle import load_lifecycle
from quant.storage.research_store import load_research_data, verify_manifest, write_json, digest_file
from quant.storage.duckdb_store import query_dataset
from quant.storage.parquet_store import read_parquet_file
from quant.version import MODEL_VERSION, FEATURE_VERSION


def recheck_held_blockers(config, prepared, start, end):
    prepared = Path(prepared)
    saved = json.loads((prepared/'prepared-inputs.json').read_text())
    if saved['model_version'] != MODEL_VERSION or saved['feature_version'] != FEATURE_VERSION:
        raise ValueError('Prepared scores do not match frozen V1')
    manifest = saved['manifest']
    # Reuse only unchanged feature/model/universe implementations and data.
    # Accounting code is deliberately current: that is what this replay tests.
    manifest = dict(manifest,source_code_sha256={k:v for k,v in manifest['source_code_sha256'].items()
        if k.replace('\\','/').startswith(('quant/features/','quant/models/','quant/universe/'))})
    verify_manifest(config,manifest)
    scores = read_parquet_file(prepared/'prepared-scores.parquet')
    prices,_,sessions,_,_ = load_research_data(config,end)
    if 'vol_63' not in scores:
        # Older compact score exports omitted the unchanged portfolio risk input.
        # Reconstruct only this trailing statistic, never refit ranks or weights.
        import numpy as np
        import pandas as pd
        from quant.universe.eligible import panels
        risks=[]
        keys={identity:set(group.as_of) for identity,group in scores.groupby('instrument_id',observed=True)}
        for panel in panels(prices[prices.instrument_id.isin(keys)],sessions):
            identity=panel.instrument_id.iloc[0]
            volatility=panel.adjusted_close.pct_change(fill_method=None).rolling(63).std(ddof=1)*np.sqrt(252)
            selected=volatility.loc[volatility.index.isin(keys[identity])]
            risks.append(pd.DataFrame(dict(as_of=selected.index,instrument_id=identity,vol_63=selected.values)))
        scores=scores.merge(pd.concat(risks,ignore_index=True),on=['as_of','instrument_id'],validate='one_to_one')
    events, transitions = load_lifecycle(config), load_transitions(config)
    output=[]
    for total_return in (False,True):
        record,folder = begin_experiment(config,'Frozen-score held-blocker diagnostic',dict(
            start=str(start),end=str(end),total_return=total_return,diagnostic_only=True,
            prepared_scores_path=str(prepared),prepared_scores_sha256=digest_file(prepared/'prepared-scores.parquet'),
            input_sha256=manifest['input_sha256']))
        try:
            actions = query_dataset(config.data_dir,'corporate_actions',end=end).drop_duplicates('event_id') if total_return else None
            run_backtest(prices,scores,sessions,start=start,end=end,cost_model=CostModel(allow_estimated_history=True),
                corporate_actions=actions,lifecycle_events=events,security_transitions=transitions,
                transition_data_dir=config.data_dir)
            record.update(decision='PATH_COMPLETED_DIAGNOSTIC_ONLY',result_summary='Full research diagnostics and seals still required')
        except (ValueError,OSError,KeyError) as error:
            record.update(decision='BLOCKED',result_summary=str(error))
            if isinstance(error,UnvaluedHolding):
                record['parameters']['blocked_holding']=dict(instrument_id=error.instrument_id,trade_date=str(error.trade_date.date()))
        write_json(folder/'outcome.json',record)
        append_experiment(config,record)
        output.append(record)
    write_json(config.data_dir/'reports/held-blocker-replay.json',dict(diagnostic_only=True,runs=output))
    return output


def main():
    from quant.pipeline.cli import parser_config
    parser,config=parser_config(__doc__)
    parser.add_argument('--prepared',required=True,type=Path)
    args=parser.parse_args()
    rows=recheck_held_blockers(args.config(config),args.prepared,args.start,args.end)
    print(json.dumps(rows,indent=2))
    return 1 if any(r['decision']=='BLOCKED' for r in rows) else 0


if __name__=='__main__':
    raise SystemExit(main())
