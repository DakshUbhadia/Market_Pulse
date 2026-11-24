"""Full history audit/rebase belongs in a separate weekly task."""
import json
import duckdb

from quant.pipeline.state import PipelineState, market_writer_lock
from quant.pipeline.check_research_ready import check_research_ready
from quant.boundaries import RAW_PRICE_START


def main():
    from quant.pipeline.cli import parser_config
    parser, config = parser_config(__doc__)
    parser.add_argument('--rebuild-adjusted', action='store_true')
    args = parser.parse_args()
    config = args.config(config)
    try:
        with market_writer_lock(config):
            if args.rebuild_adjusted:
                from quant.pipeline.build_adjusted import build_adjusted
                build_adjusted(config, RAW_PRICE_START, args.end)
            result = check_research_ready(config, as_of=args.end)
            PipelineState(config).record('weekly_integrity', status=result['status'], day=args.end,
                                         **{'from': str(RAW_PRICE_START), 'through': str(args.end)})
    except (OSError, ValueError, duckdb.Error, MemoryError) as error:
        PipelineState(config).record('weekly_integrity', status='FAILED', error=str(error))
        print(json.dumps({'status':'NOT_READY','error':str(error)}))
        return 1
    print(json.dumps({'status': result['status'], 'coverage': result['coverage']}, indent=2))
    return 0 if result['status'] == 'READY' else 1


if __name__ == '__main__':
    raise SystemExit(main())
