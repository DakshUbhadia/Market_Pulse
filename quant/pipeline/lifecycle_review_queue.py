"""Prioritize evidence review using actual holdings, deciles and observed quote gaps."""
from datetime import date
import json
import re
from pathlib import Path

import pandas as pd

from quant.storage.parquet_store import read_parquet_file, write_parquet
from quant.storage.research_store import write_json


def lifecycle_review_queue(gaps, *, holdings=None, scores=None, eligible=None, inventories=None, as_of=None):
    frame = gaps.copy()
    if inventories is not None and not inventories.empty:
        missing = inventories[inventories.symbol.notna() & ~inventories.symbol.isin(frame.symbol if 'symbol' in frame else [])]
        missing = missing.drop_duplicates('symbol')
        discovery = pd.DataFrame(dict(instrument_id=None, symbol=missing.symbol,
            last_quoted_date=pd.NaT, candidate_event='UNREVIEWED_INVENTORY_EVENT',
            economic_resolution_verified=False))
        frame = pd.concat([frame, discovery], ignore_index=True)
    if frame.empty:
        return frame.assign(source_inventory=pd.Series(dtype=str), review_priority=pd.Series(dtype=int),
                            review_status=pd.Series(dtype=str))
    def observed_ids(rows, date_column, mask=None):
        if rows is None or rows.empty:
            return set()
        rows = rows.copy()
        if as_of is not None:
            rows = rows[pd.to_datetime(rows[date_column]).le(pd.Timestamp(as_of))]
        return set(rows.loc[mask(rows) if mask else rows.index == rows.index, 'instrument_id'].dropna())
    held = observed_ids(holdings, 'trade_date', lambda f: f.quantity.gt(0) if 'quantity' in f
                        else f.value.gt(0) if 'value' in f else f.held.eq(True))
    top = observed_ids(scores, 'as_of', lambda f: f.percentile_score.ge(90))
    eligible_ids = observed_ids(eligible, 'as_of', lambda f: f.eligible.eq(True))
    frame['review_priority'] = frame.instrument_id.map(lambda name: 1 if name in held else 2 if name in top else 3 if name in eligible_ids else 4)
    # Discovery lists remain review material. Symbol matches never resolve identity.
    source_map = {}
    if inventories is not None and not inventories.empty:
        for row in inventories.to_dict('records'):
            symbol = row.get('symbol')
            if isinstance(symbol, str):
                source_map.setdefault(symbol.strip().upper(), set()).add(str(row.get('source_url', '')))
    frame['source_inventory'] = frame.symbol.map(lambda name: '|'.join(sorted(source_map.get(str(name).upper(), set()))))
    frame['review_status'] = frame.apply(lambda row: 'NEEDS_IDENTITY_REVIEW' if pd.isna(row.instrument_id)
        else 'BLOCKED_HELD_ECONOMICS' if row.review_priority == 1 and not row.economic_resolution_verified
        else 'VERIFIED_EVIDENCE' if row.economic_resolution_verified else 'NEEDS_REVIEW', axis=1)
    return frame.sort_values(['review_priority', 'last_quoted_date', 'instrument_id']).reset_index(drop=True)


def main():
    from quant.pipeline.cli import parser_config
    from quant.pipeline.audit_security_lifecycle_gaps import run_audit
    parser, config = parser_config(__doc__)
    parser.add_argument('--as-of', type=date.fromisoformat)
    for name in ('holdings', 'scores', 'eligible'):
        parser.add_argument('--'+name, type=Path)
    args = parser.parse_args()
    config, day = args.config(config), args.as_of or args.end
    gaps, _ = run_audit(config, day)
    inputs = {name: read_parquet_file(getattr(args, name)) if getattr(args, name) else None
              for name in ('holdings', 'scores', 'eligible')}
    blocked = []
    if inputs['holdings'] is None:
        # A blocked simulation may never publish holdings.parquet. Its frozen
        # outcome still proves the held identity that stopped accounting.
        for path in (config.data_dir/'research/experiments').glob('*/outcome.json'):
            outcome = json.loads(path.read_text())
            holding = outcome.get('parameters', {}).get('blocked_holding')
            if not holding:
                # Older ledgers predate structured blocked-holding metadata.
                match = re.search(r'Unvalued holding ([0-9a-f-]{36}) on (\d{4}-\d{2}-\d{2});',
                                  outcome.get('result_summary', ''))
                if match:
                    holding = dict(instrument_id=match[1], trade_date=match[2])
            if holding:
                blocked.append(dict(instrument_id=holding['instrument_id'],trade_date=holding['trade_date'],held=True))
        if blocked:
            inputs['holdings'] = pd.DataFrame(blocked)
    inventory = []
    for path in (config.data_dir/'normalized/lifecycle_inventory').rglob('*.parquet'):
        rows = read_parquet_file(path)
        # NSE list headings vary; retain raw source for independent review.
        for column in rows:
            if column.strip().lower() == 'symbol':
                rows = rows.rename(columns={column: 'symbol'})
                inventory.append(rows[['symbol', 'source_url']])
                break
    queue = lifecycle_review_queue(gaps, **inputs, inventories=pd.concat(inventory, ignore_index=True) if inventory else None, as_of=day)
    write_parquet(queue, config.data_dir/'reports/lifecycle-review-queue.parquet')
    report = dict(as_of=str(day), coverage_status='UNESTABLISHED', rows=len(queue),
                  holdings_assessment='ASSESSED' if inputs['holdings'] is not None else 'UNASSESSED',
                  holdings_source='EXPLICIT_HOLDINGS' if args.holdings else 'BLOCKED_EXPERIMENTS_ONLY',
                  priorities=queue.review_priority.value_counts().to_dict(),
                  blocked_held=int(queue.review_status.eq('BLOCKED_HELD_ECONOMICS').sum()))
    write_json(config.data_dir/'reports/lifecycle-review-queue.json', report)
    print(json.dumps(report, indent=2))
    return 1 if report['blocked_held'] else 0


if __name__ == '__main__':
    raise SystemExit(main())
