"""Gated, immutable V2 comparisons; never enables a production model."""
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4
import json
import pandas as pd

from quant.backtest.artifacts import seal_backtest
from quant.backtest.costs import CostModel
from quant.backtest.portfolio import PortfolioConfig
from quant.portfolio.constraints import RiskPolicy
from quant.backtest.engine import monthly_signal_dates
from quant.features.matrix import build_feature_matrix
from quant.features.labels import forward_labels
from quant.forward.gate import require_completed_baselines
from quant.models.factor_v2 import same_universe_scores
from quant.pipeline.build_fundamental_features import build_fundamental_features
from quant.pipeline.audit_fundamental_coverage import verify_filing_archives, audit_fundamental_coverage, coverage_dates
from quant.pipeline.check_research_ready import require_research_ready
from quant.pipeline.backfill_lifecycle import load_lifecycle
from quant.identity.transitions import load_transitions
from quant.research.specification import load_specification, research_code_hashes
from quant.research.multifactor import compare_models, v2_decision
from quant.storage.research_store import input_manifest, load_research_data, verify_manifest, digest_file, write_json, git_commit
from quant.storage.parquet_store import read_parquet_file, write_parquet
from quant.pipeline.certify_implementation import require_certified_implementation


def run_factor_v2_research(config, *, spec_path, price_baseline, total_return_baseline,
                           filings_path, anchors_path, events_path, share_coverage_path, output_root):
    folder=Path(output_root)/f'{datetime.now(timezone.utc):%Y%m%dT%H%M%S%f}-{uuid4().hex[:8]}'
    folder.mkdir(parents=True,exist_ok=False)
    try:
        spec=load_specification(spec_path)
        from quant.research.specification import verify_coverage_inputs
        verify_coverage_inputs(json.loads(Path(spec_path).read_text(encoding='utf-8')), config.data_dir)
        implementation = require_certified_implementation(config)
        baselines=require_completed_baselines(config,price_baseline,total_return_baseline)
        start=pd.Timestamp(spec['evaluation_windows'][0]['from']).date()
        end=pd.Timestamp(spec['evaluation_windows'][-1]['to']).date()
        require_research_ready(config,end,start)
        manifest=input_manifest(config,end)
        paths=[spec_path,filings_path,anchors_path,events_path,share_coverage_path]
        hashes={str(p):digest_file(p) for p in paths}
        filings,anchors,events,share_coverage=[read_parquet_file(p) for p in paths[1:]]
        from quant.pipeline.audit_share_history_coverage import verify_share_archives
        anchors, events, share_coverage = [verify_share_archives(f, config.data_dir) for f in (anchors, events, share_coverage)]
        filings=verify_filing_archives(filings,config.data_dir)
        prices,benchmark,sessions,delivery,_=load_research_data(config,end)
        lifecycle=load_lifecycle(config)
        features=build_feature_matrix(prices,benchmark,sessions,delivery=delivery,eligible_only=True,lifecycle_events=lifecycle)
        risk_features = features[['as_of','instrument_id','adv60']].copy()
        write_parquet(features[['as_of','instrument_id','adv60']],folder/'risk-features.parquet')
        dates=monthly_signal_dates(sessions)|set(coverage_dates(sessions,start,end,'monthly'))
        # The first test-session open can execute the prior month's close signal.
        # Preserve that signal and require its PIT fundamentals too.
        prior=[day for day in dates if day<pd.Timestamp(start)]
        feature_start=max(prior) if prior else pd.Timestamp(start)
        features=features[features.as_of.isin(dates) & features.as_of.between(feature_start,pd.Timestamp(end))].copy()
        # Certify the preceding year too; test dates alone cannot establish continuity.
        audit_start = feature_start-pd.DateOffset(months=12)
        from quant.pipeline.audit_fundamental_coverage import historical_coverage_universe
        coverage_universe = historical_coverage_universe(prices, sessions, audit_start.date(), end, lifecycle_events=lifecycle)
        coverage=audit_fundamental_coverage(coverage_universe,filings,sessions,start=audit_start.date(),end=end)
        write_json(folder/'filing-coverage.json',coverage)
        if not coverage['reliable_window_established'] or coverage['first_reliable_fundamental_signal_date']>str(start):
            raise ValueError('PIT filing coverage requires at least 12 consecutive passing monthly cutoffs before V2 evaluation')
        prior_coverage = [r for r in coverage['periods'] if r['as_of'] < str(start)
                          and r['as_of'] >= coverage['first_reliable_fundamental_signal_date']]
        if len(prior_coverage) < spec['coverage_policy']['minimum_consecutive_months']:
            raise ValueError('The minimum reliable filing interval must precede the first OOS result')
        from quant.pipeline.audit_share_history_coverage import audit_share_history_coverage
        shares_report = audit_share_history_coverage(coverage_universe, anchors, events, share_coverage,
            sessions, start=audit_start.date(), end=end)
        write_json(folder/'share-history-coverage.json', shares_report)
        if not shares_report['reliable_window_established'] or shares_report['first_reliable_share_signal_date'] > str(start):
            raise ValueError('Historical shares require at least 12 consecutive passing monthly cutoffs')
        if len([r for r in shares_report['periods'] if shares_report['first_reliable_share_signal_date'] <= r['as_of'] < str(start)]) < spec['coverage_policy']['minimum_consecutive_months']:
            raise ValueError('The minimum verified-share interval must precede the first OOS result')
        raw=prices.loc[prices.series.eq('EQ'),['trade_date','instrument_id','raw_close']].rename(columns={'trade_date':'as_of'})
        keys=features[['as_of','instrument_id']].merge(raw,on=['as_of','instrument_id'],validate='one_to_one')
        fundamentals=build_fundamental_features(keys,filings,anchors,events,share_coverage)
        from quant.research.factor_evidence import missingness_attribution
        write_parquet(missingness_attribution(features, fundamentals), folder/'block-missingness.parquet')
        ranked=same_universe_scores(features,fundamentals,min_group_size=spec['min_group_size'])
        for name,scores in ranked.items():
            write_parquet(scores,folder/(name+'-scores.parquet'))
        coverage_rows=[]
        for day,group in features[features.eligible].groupby('as_of'):
            covered=set(ranked['factor_v2'].loc[ranked['factor_v2'].as_of.eq(day),'instrument_id'])
            liquid=group.sort_values(['adv60','instrument_id'],ascending=[False,True]).head(100)
            coverage_rows.append(dict(as_of=day,overall=group.instrument_id.isin(covered).mean(),liquid=liquid.instrument_id.isin(covered).mean()))
        write_json(folder/'feature-coverage.json',coverage_rows)
        if not coverage_rows or any(r['overall']<.8 or r['liquid']<.9 for r in coverage_rows):
            raise ValueError('V2 feature completeness fails the per-cutoff 80% / 90% gate')
        labels=forward_labels(prices,benchmark,sessions,signal_keys=ranked['full_v1'][['as_of','instrument_id']])
        execution=dict(lifecycle_events=lifecycle,security_transitions=load_transitions(config),transition_data_dir=config.data_dir)
        return_basis=spec.get('return_basis','PRICE')
        evaluation_benchmark=benchmark
        if return_basis=='TOTAL_RETURN':
            from quant.storage.duckdb_store import query_dataset
            execution['corporate_actions']=query_dataset(config.data_dir,'corporate_actions',end=end).drop_duplicates('event_id')
            tri=query_dataset(config.data_dir,'index_tri',end=end)
            evaluation_benchmark=tri[tri.index_name.eq('NIFTY 500 TRI')]
        compared_windows=[]
        portfolio = PortfolioConfig(**spec['portfolio'])
        costs = CostModel(**spec['costs'])
        risk_policy = RiskPolicy(**spec['risk']['constraints'])
        for i,window in enumerate(spec['evaluation_windows']):
            compared,factor_ic=compare_models(prices,ranked,labels,evaluation_benchmark,sessions,window,
                cost_model=costs, portfolio=portfolio, execution=execution,return_basis=return_basis,
                risk_features=risk_features, risk_policy=risk_policy)
            compared_windows.append(compared)
            root=folder/f'window-{i:02d}'
            from quant.research.factor_evidence import factor_evidence
            evidence, correlations = factor_evidence(ranked['factor_v2'], labels, window)
            write_json(root/'factor-evidence.json', evidence)
            write_parquet(correlations, root/'factor-correlations.parquet')
            write_parquet(factor_ic,root/'factor-ic.parquet')
            if not factor_ic.empty:
                factor_ic['year']=pd.to_datetime(factor_ic.as_of).dt.year
                yearly=factor_ic.groupby(['block','year']).IC.agg(['mean','median','std','count']).reset_index()
                write_json(root/'factor-ic-yearly.json',yearly.to_dict('records'))
                factor_ic=factor_ic.sort_values(['block','as_of'])
                factor_ic['rolling_12_observations_ic']=factor_ic.groupby('block').IC.transform(lambda v:v.rolling(12,min_periods=12).mean())
                write_parquet(factor_ic,root/'factor-ic-rolling.parquet')
            for name,row in compared.items():
                arm=root/name
                write_json(arm/'metrics.json',row['metrics'])
                write_json(arm/'cost-stress.json',row['stress'])
                write_json(arm/'risk-evidence.json',row['risk_evidence'])
                write_json(arm/'risk-budgets.json',row['risk_budgets'])
                for field in ('equity_curve','trades','holdings','skipped_orders','dividends','lifecycle','security_transitions','target_orders'):
                    write_parquet(getattr(row['result'],field),arm/(field.replace('_','-')+'.parquet'))
                write_parquet(row['ic'],arm/'ic.parquet')
                write_parquet(row['deciles'],arm/'deciles.parquet')
                write_parquet(row['rolling'],arm/'rolling-excess.parquet')
            # Capital is predeclared; scenarios do not choose model weights or promotion thresholds.
            from quant.research.capacity import capacity_scenarios
            write_json(root/'capacity-scenarios.json', capacity_scenarios(prices, ranked['factor_v2'],
                risk_features, evaluation_benchmark, sessions, window, capitals=spec['capacity_scenarios'],
                portfolio=portfolio, costs=costs, policy=risk_policy, execution=execution,
                return_basis=return_basis))
        decision=v2_decision(compared_windows,spec['acceptance'])
        write_json(folder/'v2-decision.json',decision)
        verify_manifest(config,manifest)
        load_specification(spec_path)  # implementation must still match the frozen review
        if hashes!={str(p):digest_file(p) for p in paths}:
            raise ValueError('Research inputs changed during evaluation')
        write_json(folder/'config.json',dict(specification=spec,baselines=baselines,manifest=manifest,
            implementation_certification=implementation,
            extra_input_sha256=hashes,source_code_sha256=research_code_hashes(),git_commit=git_commit(),
            return_basis=return_basis,historical_cost_estimates=True,production_validated=False))
        write_json(folder/'input-manifest.json', manifest)
        write_json(folder/'specification-freeze.json', json.loads(Path(spec_path).read_text(encoding='utf-8')))
        write_json(folder/'metrics.json', {f'window-{i:02d}': {name:r['metrics'] for name,r in compared.items()}
                                          for i,compared in enumerate(compared_windows)})
        write_json(folder/'outcome.json',dict(status='COMPLETE',decision=decision))
        seal_backtest(folder)
        return folder,decision
    except (ValueError,OSError,KeyError) as error:
        write_json(folder/'outcome.json',dict(status='BLOCKED',reason=str(error),factor_v2_enabled=False))
        raise


def main():
    from quant.pipeline.cli import parser_config
    parser,config=parser_config(__doc__)
    for name in ('spec','price-baseline','total-return-baseline','filings','anchors','capital-events','share-coverage','output-root'):
        parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args()
    folder,decision=run_factor_v2_research(args.config(config),spec_path=args.spec,
        price_baseline=args.price_baseline,total_return_baseline=args.total_return_baseline,
        filings_path=args.filings,anchors_path=args.anchors,events_path=args.capital_events,
        share_coverage_path=args.share_coverage,output_root=args.output_root)
    print(json.dumps(dict(path=str(folder),decision=decision),indent=2))


if __name__=='__main__':
    main()
