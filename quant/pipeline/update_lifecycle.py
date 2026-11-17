"""Incremental lifecycle evidence import; existing event IDs cannot be overwritten."""
from quant.pipeline.backfill_lifecycle import main

if __name__ == '__main__':
    raise SystemExit(main())
