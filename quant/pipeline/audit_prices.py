"""Audit every partition against the exchange calendar, without trusting filenames."""
import json
from collections import Counter
from datetime import datetime
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

from quant.data.http import atomic_write
from quant.data.nse_bhavcopy import KEY, invalid_ohlc
from quant.data.nse_calendar import loaded_bhavcopy_evidence
from quant.pipeline.update_calendar import read_calendar


def audit_prices(config, start, end, *, write=True):
    calendar = read_calendar(config, start, end)
    expected = set(calendar.loc[calendar.is_trading_session, 'trade_date'].dt.date)
    total, duplicates, bad_ohlc, bad_close = 0, 0, 0, 0
    counts = Counter(path.stem for path in config.prices_dir.glob('year=*/month=*/*.parquet'))
    duplicate_date_keys, eq_counts = {}, {}

    def inspect(frame, candidate):
        nonlocal total, duplicates, bad_ohlc, bad_close
        total += len(frame)
        duplicates += int(frame.duplicated(KEY).sum())
        # Only multiple files claiming the same day need cross-partition key sets.
        if counts[str(candidate)] > 1:
            seen = duplicate_date_keys.setdefault(candidate, set())
            current = set(frame[KEY].itertuples(index=False, name=None))
            duplicates += len(seen & current)
            seen.update(current)
        close = pd.to_numeric(frame.close, errors='coerce')
        bad_close += int((~np.isfinite(close) | (close <= 0)).sum())
        bad_ohlc += int(invalid_ohlc(frame).sum())
        eq_counts[candidate] = frame.loc[frame.series == 'EQ', 'symbol'].nunique()

    observed, invalid = loaded_bhavcopy_evidence(config, start, end, on_frame=inspect)
    earliest, latest = (min(observed), max(observed)) if observed else (None, None)
    missing = sorted(expected - observed.keys())
    unexpected = sorted(observed.keys() - expected)
    coverage = 100 * len(expected & observed.keys()) / len(expected) if expected else 0.0
    report = {
        'from': str(start), 'to': str(end), 'expected_sessions': len(expected),
        'loaded_sessions': len(expected & observed.keys()), 'missing_sessions': list(map(str, missing)),
        'unexpected_sessions': list(map(str, unexpected)), 'coverage_percent': coverage,
        'total_rows': total, 'duplicate_keys': duplicates, 'invalid_ohlc_rows': bad_ohlc,
        'invalid_close_values': bad_close, 'corrupt_partitions': invalid,
        'earliest_date': str(earliest) if earliest else None,
        'latest_date': str(latest) if latest else None, 'latest_eq_symbol_count': int(eq_counts.get(latest, 0)),
        'status': 'READY' if (expected and coverage >= 99.5 and not
                              (duplicates or bad_ohlc or bad_close or invalid or unexpected)) else 'NOT_READY',
    }
    if write:
        now = datetime.now(ZoneInfo(config.timezone))
        atomic_write(config.data_dir / 'reports' / f'price-audit-{now:%Y%m%d}.json',
                     json.dumps(report, indent=2).encode())
    return report


def main():
    from quant.pipeline.cli import parser_config
    parser, config = parser_config(__doc__)
    args = parser.parse_args()
    config = args.config(config)
    try:
        report = audit_prices(config, args.start, args.end)
    except (ValueError, OSError) as error:
        print(f'Price audit failed: {error}')
        return 1
    print(json.dumps(report, indent=2))
    return 0 if report['status'] == 'READY' else 1


if __name__ == '__main__':
    raise SystemExit(main())
