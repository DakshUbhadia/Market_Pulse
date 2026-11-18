"""Resume document acquisition from preserved metadata with a bounded batch.

Discovery completeness and document/parser completeness are separate statuses.
Each filing is published and checkpointed before proceeding to the next.
"""
import json
import pandas as pd
from quant.data.nse_client import NseClient, RawResponse
from quant.data.financial_versions import FinancialVersionStore
from quant.pipeline.update_corporate import archive_filings
from quant.pipeline.state import state_lock
from quant.storage.parquet_store import read_parquet_file
from quant.storage.research_store import write_json


def backfill_documents(config, start, end, *, limit=100, retry_review=False):
    if limit < 1 or start > end:
        raise ValueError('Invalid document batch')
    files = sorted((config.data_dir/'normalized/financials').rglob('*.parquet'))
    frame = pd.concat([read_parquet_file(p) for p in files],ignore_index=True) if files else pd.DataFrame()
    checkpoint = config.data_dir/'state/fundamental_backfill'/f'documents-{start}-{end}.json'
    with state_lock(checkpoint.with_suffix('.lock')):
        state = json.loads(checkpoint.read_text()) if checkpoint.exists() else dict(attempted={})
        if frame.empty:
            raise ValueError('Run metadata discovery first')
        frame = frame.sort_values('first_seen_at').drop_duplicates('filing_id',keep='last')
        times = pd.to_datetime(frame.exchange_disseminated_at,utc=True,errors='coerce')
        selected = frame[times.ge(pd.Timestamp(start,tz='Asia/Kolkata')) & times.lt(pd.Timestamp(end,tz='Asia/Kolkata')+pd.Timedelta(days=1))]
        candidates = selected[selected.source_document.map(lambda x:isinstance(x,str) and bool(x.strip()))]
        if 'document_sha256' in candidates:
            candidates = candidates[candidates.document_sha256.isna()]
        if not retry_review:
            candidates = candidates[~candidates.filing_id.isin(state['attempted'])]
        history = read_parquet_file(config.data_dir/'normalized/security_history/identities.parquet')
        versions = FinancialVersionStore(config)
        with NseClient(config) as client:
            for row in candidates.head(limit).to_dict('records'):
                key = row['filing_id']
                # Metadata IDs must remain stable when FinancialVersionStore derives document IDs.
                row['filing_id'] = row.get('metadata_filing_id') or key
                parsed, review = archive_filings(client,pd.DataFrame([row]),'financials',history)
                from datetime import datetime, timezone
                observed = datetime.now(timezone.utc).isoformat()
                raw = RawResponse(row['source_url'],observed,row['source_sha256'],
                    config.data_dir/row['metadata_raw_path'],200)
                versions.publish(parsed,raw)
                state['attempted'][key] = dict(parser_status=parsed.iloc[0].get('parser_status'),
                    document_sha256=parsed.iloc[0].get('document_sha256'),review=review)
                write_json(checkpoint,state)
        report = dict(status='PARTIAL' if len(candidates)>limit else 'BATCH_EXHAUSTED',
            requested_range=dict(start=str(start),end=str(end)),checkpoint=str(checkpoint),
            batch_limit=limit,attempted_total=len(state['attempted']),remaining_unattempted=max(0,len(candidates)-limit),
            parsed=sum(r.get('parser_status')=='PARSED' for r in state['attempted'].values()),
            needs_review=sum(r.get('parser_status')!='PARSED' for r in state['attempted'].values()),
            source_documents_preserved=sum(isinstance(r.get('document_sha256'),str) for r in state['attempted'].values()),
            coverage_status='UNASSESSED_RUN_UNIVERSE_COVERAGE',factor_v2_enabled=False)
        write_json(config.data_dir/'reports/fundamental-document-backfill-status.json',report)
        return report


def main():
    from quant.pipeline.cli import parser_config
    parser,config = parser_config(__doc__)
    parser.add_argument('--limit',type=int,default=100)
    parser.add_argument('--retry-review',action='store_true')
    args = parser.parse_args()
    result = backfill_documents(args.config(config),args.start,args.end,limit=args.limit,retry_review=args.retry_review)
    print(json.dumps(result,indent=2))
    return 0 if result['status']=='BATCH_EXHAUSTED' and result['needs_review']==0 else 1


if __name__ == '__main__':
    raise SystemExit(main())
