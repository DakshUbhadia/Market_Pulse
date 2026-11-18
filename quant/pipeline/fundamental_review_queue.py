"""Prioritize filing issues using a dated universe, never current classifications."""
import pandas as pd


def fundamental_review_queue(filings, universe, as_of):
    cross = universe[pd.to_datetime(universe.as_of).eq(pd.Timestamp(as_of)) & universe.eligible].copy()
    liquid = set(cross.sort_values(['adv60','instrument_id'],ascending=[False,True]).head(100).instrument_id)
    financials = set(cross.loc[cross.entity_type.isin(['bank','nbfc']),'instrument_id']) if 'entity_type' in cross else set()
    rows = []
    for identity in sorted(set(cross.instrument_id)):
        known = filings[filings.instrument_id.eq(identity)].copy() if not filings.empty else filings
        # Availability and failures must be known at the review cutoff.
        if not known.empty:
            times = pd.to_datetime(known.exchange_disseminated_at,utc=True,errors='coerce')
            known = known[times.le(pd.Timestamp(as_of).tz_localize('Asia/Kolkata')+pd.Timedelta(hours=15,minutes=30))]
        problems = []
        if known.empty:
            problems.append('NO_KNOWN_FILING')
        else:
            failures = known.get('parser_status',pd.Series('NEEDS_REVIEW',index=known.index)).ne('PARSED')
            if failures.any():
                problems.append('PERSISTENT_PARSER_FAILURE' if failures.sum()>1 else 'PARSER_REVIEW')
            if 'timing_status' in known and known.timing_status.astype(str).str.contains('REVISION').any():
                problems.append('AMBIGUOUS_REVISION')
            for field, label in [('revision_timing_uncertain','AMBIGUOUS_REVISION'),('unsupported_concepts','UNSUPPORTED_CONCEPTS')]:
                if field in known and known[field].fillna(False).astype(bool).any():
                    problems.append(label)
        if problems:
            rows.append(dict(instrument_id=identity,as_of=str(as_of),top100_adv=identity in liquid,
                financial=identity in financials,reasons=problems,
                priority=(0 if identity in liquid else 1 if identity in financials else 2)))
    return sorted(rows,key=lambda r:(r['priority'], 'PERSISTENT_PARSER_FAILURE' not in r['reasons'],r['instrument_id']))


def main():
    import json
    from pathlib import Path
    from quant.pipeline.cli import parser_config
    from quant.storage.parquet_store import read_parquet_file
    from quant.storage.duckdb_store import query_dataset
    from quant.storage.research_store import write_json
    parser, config = parser_config(__doc__)
    parser.add_argument('--universe',type=Path,required=True)
    args = parser.parse_args()
    config = args.config(config)
    try:
        filings = query_dataset(config.data_dir,'financials',end=args.end)
    except FileNotFoundError:
        filings = pd.DataFrame()
    rows = fundamental_review_queue(filings,read_parquet_file(args.universe),args.end)
    report = dict(as_of=str(args.end),items=rows,factor_v2_enabled=False)
    write_json(config.data_dir/'reports/fundamental-review-queue.json',report)
    print(json.dumps(report,indent=2))


if __name__ == '__main__':
    main()
