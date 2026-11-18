"""Finite Stage 1 batches with checkpoints and automatic source/parser stops."""
from datetime import date
import json
import os
from datetime import datetime,timezone

from quant.pipeline.backfill_fundamental_documents import backfill_documents
from quant.storage.research_store import write_json


def acquire_stage1(config,start,end,*,batch_size=100,max_batches=1):
    if start<date(2024,1,1) or not 1<=batch_size<=250 or not 1<=max_batches<=250:
        raise ValueError('Stage 1 requires 2024-present and bounded document/batch limits')
    results=[]
    status='BATCH_BUDGET_REACHED'
    checkpoint=config.data_dir/'state/fundamental_backfill'/f'documents-{start}-{end}.json'
    progress=config.data_dir/'reports/fundamental-stage1-acquisition.json'
    write_json(progress,dict(status='RUNNING',pid=os.getpid(),started_at=datetime.now(timezone.utc).isoformat(),
        start=str(start),end=str(end),batch_size=batch_size,max_batches=max_batches,batches_completed=0))
    for _ in range(max_batches):
        before=json.loads(checkpoint.read_text()).get('attempted',{}) if checkpoint.exists() else {}
        previous_parsed=sum(r.get('parser_status')=='PARSED' for r in before.values())
        report=backfill_documents(config,start,end,limit=batch_size)
        count=report['attempted_this_batch']
        parsed=report['parsed']-previous_parsed
        results.append(dict(**report,batch_parse_success=parsed/count if count else None))
        write_json(progress,dict(status='RUNNING',pid=os.getpid(),start=str(start),end=str(end),
            batches_completed=len(results),last_batch=results[-1],factor_v2_enabled=False))
        if report['status']=='BLOCKED_SOURCE':
            status='LIVE_SOURCE_UNAVAILABLE'
        elif count and parsed/count<.8:
            status='PARSER_REVIEW_REQUIRED'
        elif report['remaining_unattempted']==0:
            status='ACQUIRED_WITH_REVIEW' if report['needs_review'] else 'ACQUISITION_EXHAUSTED'
        if status!='BATCH_BUDGET_REACHED':
            break
    result=dict(status=status,pid=os.getpid(),range=dict(start=str(start),end=str(end)),batches=results,
        historical_expansion_enabled=False,factor_v2_enabled=False,
        coverage_status='UNASSESSED_REQUIRES_DATED_UNIVERSE_AUDIT')
    write_json(config.data_dir/'reports/fundamental-stage1-acquisition.json',result)
    return result


def main():
    from quant.pipeline.cli import parser_config
    parser,config=parser_config(__doc__)
    parser.set_defaults(start=date(2024,1,1))
    parser.add_argument('--batch-size',type=int,default=100)
    parser.add_argument('--max-batches',type=int,default=1)
    args=parser.parse_args()
    report=acquire_stage1(args.config(config),args.start,args.end,batch_size=args.batch_size,max_batches=args.max_batches)
    print(json.dumps(report,indent=2))
    return 0 if report['status'] in ('BATCH_BUDGET_REACHED','ACQUISITION_EXHAUSTED','ACQUIRED_WITH_REVIEW') else 1


if __name__=='__main__':
    raise SystemExit(main())
