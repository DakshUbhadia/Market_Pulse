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


def backfill_documents(config, start, end, *, limit=100, retry_review=False, plan_path=None):
    if limit < 1 or start > end:
        raise ValueError('Invalid document batch')
    files = sorted((config.data_dir/'normalized/financials').rglob('*.parquet'))
    frame = pd.concat([read_parquet_file(p) for p in files],ignore_index=True) if files else pd.DataFrame()
    checkpoint = config.data_dir/'state/fundamental_backfill'/f'documents-{start}-{end}.json'
    with state_lock(checkpoint.with_suffix('.lock')):
        state = json.loads(checkpoint.read_text()) if checkpoint.exists() else dict(attempted={})
        if frame.empty:
            raise ValueError('Run metadata discovery first')
        if plan_path is not None:
            from quant.pipeline.plan_fundamental_acquisition import load_plan, acquisition_state_hash
            plan = load_plan(plan_path)
            if plan.get('acquisition_state_sha256') != acquisition_state_hash(frame, state['attempted']):
                raise ValueError('Acquisition plan is stale; parse, normalize, audit coverage, recompute ceiling and rebuild plan')
        frame = frame.sort_values('first_seen_at').drop_duplicates('filing_id',keep='last')
        times = pd.to_datetime(frame.exchange_disseminated_at,utc=True,errors='coerce')
        selected = frame[times.isna() | (times.ge(pd.Timestamp(start,tz='Asia/Kolkata')) & times.lt(pd.Timestamp(end,tz='Asia/Kolkata')+pd.Timedelta(days=1)))]
        from quant.research.coverage_deficits import candidate_id
        selected = selected.copy()
        selected['_candidate_id'] = [candidate_id(row) for row in selected.to_dict('records')]
        declaration = config.data_dir/'state/fundamental_backfill'/f'stage1-candidates-{start}-{end}.json'
        if declaration.exists():
            from quant.forward.signal_store import content_hash
            scope = json.loads(declaration.read_text(encoding='utf-8'))
            if scope.get('sha256') != content_hash({k: v for k, v in scope.items() if k != 'sha256'}):
                raise ValueError('Stage 1 candidate declaration checksum changed')
            selected = selected[selected._candidate_id.isin(scope['candidate_ids'])]
        candidates = selected  # Missing document URLs must receive an explicit review classification too.
        if 'document_sha256' in candidates:
            candidates = candidates[candidates.document_sha256.isna()]
        if not retry_review:
            candidates = candidates[~candidates._candidate_id.isin(state['attempted']) & ~candidates.filing_id.isin(state['attempted'])]
        else:
            from quant.pipeline.report_fundamental_acquisition import classify_attempt
            permanent = {key for key, attempt in state['attempted'].items() if not classify_attempt(attempt)[1]}
            candidates = candidates[~candidates._candidate_id.isin(permanent) & ~candidates.filing_id.isin(permanent)]
        if plan_path is not None:
            from quant.pipeline.plan_fundamental_acquisition import load_plan
            from quant.research.coverage_deficits import candidate_id
            plan = load_plan(plan_path)
            priorities = {r['filing_id']: r['priority_rank'] for r in plan['candidates']}
            candidates = candidates[candidates._candidate_id.isin(priorities)].copy()
            candidates['_priority'] = [priorities.get(candidate_id(r), len(priorities)+1) for r in candidates.to_dict('records')]
            candidates = candidates.sort_values(['_priority', 'filing_id']).drop(columns='_priority')
        history = read_parquet_file(config.data_dir/'normalized/security_history/identities.parquet')
        versions = FinancialVersionStore(config)
        attempted_this_batch, source_blocked = 0, False
        with NseClient(config) as client:
            for row in candidates.head(limit).to_dict('records'):
                key = row.pop('_candidate_id')
                # Metadata IDs must remain stable when FinancialVersionStore derives document IDs.
                row['filing_id'] = row.get('metadata_filing_id') or key
                parsed, review = archive_filings(client,pd.DataFrame([row]),'financials',history)
                from datetime import datetime, timezone
                observed = datetime.now(timezone.utc).isoformat()
                raw = RawResponse(row['source_url'],observed,row['source_sha256'],
                    config.data_dir/row['metadata_raw_path'],200)
                versions.publish(parsed,raw)
                state['attempted'][key] = dict(parser_status=parsed.iloc[0].get('parser_status'),
                    document_sha256=parsed.iloc[0].get('document_sha256'),review=review,
                    attempt_count=state['attempted'].get(key, {}).get('attempt_count', 0)+1,
                    last_attempted_at=observed)
                write_json(checkpoint,state)
                attempted_this_batch += 1
                if any(r.get('source_status')=='LIVE_SOURCE_UNAVAILABLE' for r in review):
                    source_blocked = True
                    break
        report = dict(status='BLOCKED_SOURCE' if source_blocked else 'PARTIAL' if len(candidates)>attempted_this_batch else 'BATCH_EXHAUSTED',
            requested_range=dict(start=str(start),end=str(end)),checkpoint=str(checkpoint),
            batch_limit=limit,attempted_this_batch=attempted_this_batch,
            attempted_total=len(state['attempted']),remaining_unattempted=max(0,len(candidates)-attempted_this_batch),
            parsed=sum(r.get('parser_status')=='PARSED' for r in state['attempted'].values()),
            needs_review=sum(r.get('parser_status')!='PARSED' for r in state['attempted'].values()),
            source_documents_preserved=sum(isinstance(r.get('document_sha256'),str) for r in state['attempted'].values()),
            coverage_status='UNASSESSED_RUN_UNIVERSE_COVERAGE',factor_v2_enabled=False)
        write_json(config.data_dir/'reports/fundamental-document-backfill-status.json',report)
        from quant.pipeline.report_fundamental_parser_stability import report_parser_stability
        report_parser_stability(config,start,end)
        return report


def main():
    from quant.pipeline.cli import parser_config
    parser,config = parser_config(__doc__)
    parser.add_argument('--limit',type=int,default=100)
    parser.add_argument('--retry-review',action='store_true')
    from pathlib import Path
    parser.add_argument('--plan', type=Path)
    args = parser.parse_args()
    result = backfill_documents(args.config(config),args.start,args.end,limit=args.limit,retry_review=args.retry_review,plan_path=args.plan)
    print(json.dumps(result,indent=2))
    return 0 if result['status']=='BATCH_EXHAUSTED' and result['needs_review']==0 else 1


if __name__ == '__main__':
    raise SystemExit(main())
