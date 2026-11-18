"""Measure bounded document attempts; discovery is not parser stability."""
import json
from collections import Counter
from pathlib import Path
import pandas as pd
from quant.storage.parquet_store import read_parquet_file
from quant.storage.research_store import write_json, digest_file


def parser_stability(filings, attempts, *, universe=None, as_of=None):
    frame=filings.sort_values('first_seen_at').drop_duplicates('filing_id',keep='last') if not filings.empty else filings
    indexed={} if frame.empty else {r['filing_id']:r for r in frame.to_dict('records')}
    reasons,entities,taxonomies,periods=Counter(),Counter(),Counter(),Counter()
    parsed=downloaded=timing=identity=0
    details=[]
    for key,attempt in attempts.items():
        row=indexed.get(key,{})
        digest=attempt.get('document_sha256')
        if isinstance(digest,str) and 'document_sha256' in frame:
            versions=frame[frame.document_sha256.eq(digest)]
            if len(versions):
                row=versions.iloc[-1].to_dict()
        ok=attempt.get('parser_status')=='PARSED'
        parsed+=ok
        downloaded+=isinstance(digest,str)
        timing+=row.get('timing_status')=='VERIFIED'
        resolved=isinstance(row.get('instrument_id'),str) and bool(row['instrument_id'])
        identity+=resolved
        entity='BANK' if row.get('financial_schema')=='BANK' or row.get('bank') is True else row.get('financial_schema','UNKNOWN')
        taxonomy=attempt.get('taxonomy','UNASSESSED_ARCHIVED_DOCUMENT')
        period=str(row.get('period_semantics') or row.get('period_type') or 'UNKNOWN')
        failures=[r.get('reason','UNCLASSIFIED') for r in attempt.get('review',[])]
        if not ok:
            reasons.update(set(failures or ['UNCLASSIFIED']))
            entities[str(entity)]+=1
            taxonomies[str(taxonomy)]+=1
            periods[period]+=1
        details.append(dict(filing_id=key,instrument_id=row.get('instrument_id'),parsed=ok,
            downloaded=isinstance(digest,str),entity_type=str(entity),taxonomy=taxonomy,period_type=period,reasons=failures))
    n=len(attempts)
    liquid=[]
    if universe is not None and not universe.empty and as_of is not None:
        cross=universe[pd.to_datetime(universe.as_of).eq(pd.Timestamp(as_of)) & universe.eligible]
        for name in cross.sort_values(['adv60','instrument_id'],ascending=[False,True]).head(100).instrument_id:
            bad=[r for r in details if r['instrument_id']==name and not r['parsed']]
            has_parsed=any(r['instrument_id']==name and r['parsed'] for r in details)
            if bad or not has_parsed:
                liquid.append(dict(instrument_id=name,unresolved_attempts=len(bad),
                    reason='UNRESOLVED_ATTEMPTS' if bad else 'NO_PARSED_DOCUMENT_IN_ATTEMPTED_BATCH'))
    return dict(documents_attempted=n,documents_downloaded=downloaded,parsed=parsed,needs_review=n-parsed,
        parse_success_pct=100*parsed/n if n else None,timing_verified_pct=100*timing/n if n else None,
        identity_resolved_pct=100*identity/n if n else None,failure_by_reason=dict(reasons),
        failure_by_entity_type=dict(entities),failure_by_taxonomy=dict(taxonomies),failure_by_period_type=dict(periods),
        top100_adv_unresolved_filings=liquid,liquidity_assessment='ASSESSED' if universe is not None else 'UNASSESSED',
        denominator='CHECKPOINTED_DOCUMENT_ATTEMPTS',details=details,parser_stability='UNESTABLISHED',
        date_range_expansion_allowed=False,factor_v2_enabled=False)


def report_parser_stability(config,start,end,universe_path=None):
    checkpoint=config.data_dir/'state/fundamental_backfill'/f'documents-{start}-{end}.json'
    attempts=json.loads(checkpoint.read_text())['attempted'] if checkpoint.exists() else {}
    files=sorted((config.data_dir/'normalized/financials').rglob('*.parquet'))
    frame=pd.concat([read_parquet_file(p) for p in files],ignore_index=True) if files else pd.DataFrame()
    # Identify taxonomy from preserved, checksum-verified instances, not URL names.
    from quant.data.xbrl import parse_xbrl
    for attempt in attempts.values():
        digest=attempt.get('document_sha256')
        if isinstance(digest,str) and 'document_sha256' in frame:
            rows=frame[frame.document_sha256.eq(digest)]
            if len(rows):
                path=Path(rows.iloc[-1].document_raw_path)
                path=path if path.is_absolute() else config.data_dir/path
                try:
                    if not path.resolve().is_relative_to(config.data_dir.resolve()) or digest_file(path)!=digest:
                        raise ValueError('Archive checksum mismatch')
                    attempt['taxonomy']=';'.join(sorted({f['namespace'] for f in parse_xbrl(path.read_bytes())})) or 'NO_FACT_NAMESPACE'
                except (OSError,ValueError) as error:
                    attempt['taxonomy']='UNASSESSED: '+str(error)
    universe=read_parquet_file(universe_path) if universe_path else None
    report=parser_stability(frame,attempts,universe=universe,as_of=end)
    report.update(requested_range=dict(start=str(start),end=str(end)),checkpoint=str(checkpoint),
        universe_source=str(universe_path) if universe_path else None,
        checkpoint_sha256=digest_file(checkpoint) if checkpoint.exists() else None)
    write_json(config.data_dir/'reports/fundamental-parser-stability.json',report)
    return report


def main():
    from quant.pipeline.cli import parser_config
    parser,config=parser_config(__doc__)
    parser.add_argument('--universe',type=Path)
    args=parser.parse_args()
    report=report_parser_stability(args.config(config),args.start,args.end,args.universe)
    print(json.dumps({k:v for k,v in report.items() if k!='details'},indent=2))


if __name__=='__main__':
    main()
