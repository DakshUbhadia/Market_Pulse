"""Compare simple V2 with declared risk targets after its evidence gate."""
from dataclasses import asdict
from datetime import date,datetime,timezone
from pathlib import Path
from uuid import uuid4
import json
import math

from quant.backtest.artifacts import verify_backtest_seal,seal_backtest
from quant.backtest.engine import run_backtest
from quant.backtest.costs import CostModel
from quant.backtest.portfolio import PortfolioConfig
from quant.backtest.metrics import performance_metrics
from quant.backtest.benchmarks import index_returns,total_return_index_returns
from quant.pipeline.backfill_lifecycle import load_lifecycle
from quant.identity.transitions import load_transitions
from quant.portfolio.constraints import RiskPolicy
from quant.portfolio.target import risk_target_builder
from quant.research.specification import load_specification,research_code_hashes
from quant.storage.research_store import load_research_data,verify_manifest,write_json,digest_file,git_commit
from quant.storage.parquet_store import read_parquet_file,write_parquet


def run_portfolio_risk_research(config,v2_experiment,spec_path,output_root):
    root=Path(v2_experiment)
    verify_backtest_seal(root)
    decision=json.loads((root/'v2-decision.json').read_text())
    if decision.get('decision')!='GO_FURTHER_V2_RESEARCH':
        raise ValueError('V2 evidence gate blocks portfolio-risk experiments')
    spec=load_specification(spec_path)
    frozen_spec_sha256=digest_file(spec_path)
    risk=spec.get('risk') or {}
    capital=risk.get('capital')
    if not isinstance(capital,(int,float)) or not math.isfinite(capital) or capital<=0:
        raise ValueError('Reviewed risk specification requires explicit positive capital')
    if risk.get('volatility_targets')!=[.12,.15]:
        raise ValueError('Initial risk comparison requires the declared 12% / 15% targets')
    configuration=json.loads((root/'config.json').read_text())
    manifest=configuration['manifest']
    verify_manifest(config,manifest)
    scores=read_parquet_file(root/'factor_v2-scores.parquet')
    end=date.fromisoformat(max(w['to'] for w in spec['evaluation_windows']))
    prices,benchmark,sessions,_,_=load_research_data(config,end)
    actions=None
    if configuration['return_basis']=='TOTAL_RETURN':
        from quant.storage.duckdb_store import query_dataset
        actions=query_dataset(config.data_dir,'corporate_actions',end=end).drop_duplicates('event_id')
        tri=query_dataset(config.data_dir,'index_tri',end=end)
        benchmark=tri[tri.index_name.eq('NIFTY 500 TRI')]
    features=read_parquet_file(root/'risk-features.parquet')
    folder=Path(output_root)/f'{datetime.now(timezone.utc):%Y%m%dT%H%M%S%f}-{uuid4().hex[:8]}'
    folder.mkdir(parents=True,exist_ok=False)
    try:
        output=[]
        for index,window in enumerate(spec['evaluation_windows']):
            for volatility in (None,.12,.15):
                name='simple_inverse_volatility' if volatility is None else f'volatility_{volatility:.2f}'
                policy=RiskPolicy(**dict(risk.get('constraints',{}),target_volatility=volatility or .15))
                callback,reports=(None,[]) if volatility is None else risk_target_builder(prices,features,sessions,policy)
                result=run_backtest(prices,scores,sessions,start=window['from'],end=window['to'],
                    portfolio=PortfolioConfig(initial_cash=capital,max_weight=policy.max_weight),
                    cost_model=CostModel(allow_estimated_history=True),target_builder=callback,
                    target_builder_context=callback is not None,lifecycle_events=load_lifecycle(config),
                    security_transitions=load_transitions(config),transition_data_dir=config.data_dir,corporate_actions=actions)
                market=(index_returns(benchmark,result.equity_curve.trade_date) if actions is None else total_return_index_returns(benchmark,result.equity_curve.trade_date,sessions))
                metrics,_=performance_metrics(result.equity_curve,market,result.trades)
                arm=folder/f'window-{index:02d}'/name
                for field in ('equity_curve','trades','holdings','skipped_orders','security_transitions'):
                    write_parquet(getattr(result,field),arm/(field+'.parquet'))
                write_json(arm/'risk-budgets.json',reports)
                if not result.trades.empty:
                    realized=result.trades.merge(features.rename(columns={'as_of':'signal_date'}),
                        on=['signal_date','instrument_id'],how='left',validate='many_to_one')
                    realized['participation']=realized.turnover/realized.adv60
                    write_parquet(realized,arm/'realized-capacity.parquet')
                    if volatility is not None and (realized.adv60.isna().any() or (realized.participation>policy.adv_fraction+1e-9).any()):
                        raise ValueError('Realized next-open orders violate the declared ADV capacity rule')
                output.append(dict(window=window,variant=name,metrics=metrics,capital=capital,policy=asdict(policy)))
        verify_manifest(config,manifest)
        verify_backtest_seal(root)
        load_specification(spec_path)
        if digest_file(spec_path)!=frozen_spec_sha256:
            raise ValueError('Risk specification changed during evaluation')
        write_json(folder/'comparison.json',dict(status='RESEARCH_ONLY',results=output,
            v2_completion_sha256=digest_file(root/'completion.json'),spec_sha256=digest_file(spec_path),
            specification=spec,source_code_sha256=research_code_hashes(),git_commit=git_commit(),
            source_manifest=manifest,
            capacity_scope='TARGET_AND_REALIZED_ORDERS; violations block completion',
            automatic_promotion=False))
        seal_backtest(folder)
        return folder
    except (ValueError,OSError,KeyError) as error:
        write_json(folder/'outcome.json',dict(status='BLOCKED',reason=str(error)))
        raise


def main():
    from quant.pipeline.cli import parser_config
    parser,config=parser_config(__doc__)
    for name in ('v2-experiment','spec','output-root'):
        parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args()
    print(run_portfolio_risk_research(args.config(config),args.v2_experiment,args.spec,args.output_root))


if __name__=='__main__':
    main()
