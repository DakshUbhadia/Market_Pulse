"""Full history audit/rebase belongs in a separate weekly task."""
import json
from datetime import date
import duckdb

from quant.pipeline.state import PipelineState
from quant.pipeline.check_research_ready import check_research_ready


def main():
    from quant.pipeline.cli import parser_config
    parser, config = parser_config(__doc__)
    parser.add_argument('--rebuild-adjusted', action='store_true')
    args = parser.parse_args()
    config = args.config(config)
    try:
        if args.rebuild_adjusted:
            from quant.pipeline.build_adjusted import build_adjusted
            build_adjusted(config, date(2010, 1, 1), args.end)
        result = check_research_ready(config, as_of=args.end)
    except (OSError, ValueError, duckdb.Error, MemoryError) as error:
        PipelineState(config).record('weekly_integrity', status='FAILED', error=str(error))
        print(json.dumps({'status':'NOT_READY','error':str(error)}))
        return 1
    PipelineState(config).record('weekly_integrity', status=result['status'], day=args.end,
                                 **{'from': '2010-01-01', 'through': str(args.end)})
    print(json.dumps({'status': result['status'], 'coverage': result['coverage']}, indent=2))
    return 0 if result['status'] == 'READY' else 1


if __name__ == '__main__':
    raise SystemExit(main())
