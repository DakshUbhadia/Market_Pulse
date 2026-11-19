"""Preserve a reviewed evidence-search audit without modifying experiments."""
import json
from pathlib import Path
from quant.research.evaluation_window import record_search_audit


def main():
    from quant.pipeline.cli import parser_config
    parser, config = parser_config(__doc__)
    parser.add_argument('--audit', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    record_search_audit(json.loads(args.audit.read_text(encoding='utf-8')), args.output,
                        data_dir=args.config(config).data_dir)
    print(args.output)


if __name__ == '__main__':
    main()
