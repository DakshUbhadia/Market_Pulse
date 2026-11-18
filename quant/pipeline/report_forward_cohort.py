"""Read frozen cohort evidence and summarize maturity without promoting production."""
import json
import pandas as pd
from quant.forward.cohort import cohort_root, cohort_report
from quant.forward.metrics import forward_metrics
from quant.forward.signal_store import content_hash, read_signals
from quant.storage.research_store import write_json


def report_forward_cohort(config, as_of, cohort=None):
    root = cohort_root(config,cohort)
    report = forward_metrics(root)
    batches, _ = read_signals(root)
    report.update(cohort=cohort,as_of=str(as_of),status='ACTIVE' if batches else 'NOT_STARTED',
        cohort_age_calendar_days=(pd.Timestamp(as_of)-pd.Timestamp(min(b['as_of'] for b in batches))).days if batches else 0)
    if any(pd.Timestamp(b['as_of']) > pd.Timestamp(as_of) for b in batches):
        raise ValueError('Report cutoff predates frozen cohort observations')
    shadows = []
    for path in sorted((root/'shadow').glob('*.json')):
        row = json.loads(path.read_text())
        if content_hash({k:v for k,v in row.items() if k != 'sha256'}) != row['sha256']:
            raise ValueError('Shadow checksum changed')
        if pd.Timestamp(row['as_of']) <= pd.Timestamp(as_of):
            shadows.append(row)
    for horizon in (21,63):
        rows = [json.loads(p.read_text()) for p in (root/'outcomes').glob(f'*/{horizon}.json')]
        rows = [r for r in rows if pd.Timestamp(r['exit_date']) <= pd.Timestamp(as_of)]
        frame = pd.DataFrame(rows)
        stats = report['outcomes'][str(horizon)]
        for name, column in [('mean_excess_return','cost_adjusted_excess_return'),
            ('median_excess_return','cost_adjusted_excess_return'),('MAE','maximum_adverse_excursion'),
            ('MFE','maximum_favorable_excursion')]:
            stats[name] = float(frame[column].median() if name.startswith('median') else frame[column].mean()) if len(frame) else None
        stats['hit_rate'] = float(frame.cost_adjusted_excess_return.gt(0).mean()) if len(frame) else None
    curve = pd.DataFrame([dict(as_of=r['as_of'],**r['equity']) for r in shadows])
    report['executed_recommendations'] = sum(t['side']=='BUY' for r in shadows for t in r['trades'])
    report['lifecycle_events'] = sum(len(r.get('lifecycle',[])) for r in shadows)
    report['shadow_portfolio_return'] = None
    report['drawdown'] = None
    report['turnover'] = None
    report['cost_drag'] = None
    if len(curve):
        initial = shadows[0]['settings']['portfolio']['initial_cash']
        nav = pd.concat([pd.Series([initial]),curve.nav],ignore_index=True)
        report.update(shadow_portfolio_return=float(nav.iloc[-1]/initial-1),
            drawdown=float((nav/nav.cummax()-1).min()),turnover=float(curve.turnover.sum()),
            cost_drag=sum(t.get('total',0) for r in shadows for t in r['trades'])/initial)
    # A benchmark must have the same entry convention and interval; do not substitute outcome averages.
    report['benchmark_excess'] = None
    report['benchmark_status'] = 'UNASSESSED_MATCHED_SHADOW_BENCHMARK_REQUIRED'
    if len(curve):
        from quant.storage.duckdb_store import query_dataset
        try:
            benchmark=query_dataset(config.data_dir,'index_tri',start=pd.Timestamp(curve.as_of.iloc[0]).date(),end=as_of)
            benchmark=benchmark[benchmark.index_name.eq('NIFTY 500 TRI')].set_index('trade_date')
            closes=benchmark.reindex(pd.to_datetime(curve.as_of)).close
            if closes.isna().any() or (closes<=0).any() or closes.index.duplicated().any():
                raise ValueError('Incomplete matched TRI sessions')
            report['benchmark_excess']=report['shadow_portfolio_return']-float(closes.iloc[-1]/closes.iloc[0]-1)
            report['benchmark_status']='GROSS_TRI_SIGNAL_CLOSE_TO_SHADOW_CLOSE'
        except (FileNotFoundError,ValueError,KeyError) as error:
            report['benchmark_error']=str(error)
    outcome_report = cohort_report(config,cohort,'forward-outcomes.json')
    report['blocked_outcomes'] = json.loads(outcome_report.read_text()).get('blocked',[]) if outcome_report.exists() else []
    report['automatic_production_promotion'] = False
    write_json(cohort_report(config,cohort,'forward-cohort.json'),report)
    return report


def main():
    from quant.pipeline.cli import parser_config
    parser,config = parser_config(__doc__)
    parser.add_argument('--cohort')
    args = parser.parse_args()
    print(json.dumps(report_forward_cohort(args.config(config),args.end,args.cohort),indent=2))


if __name__ == '__main__':
    main()
