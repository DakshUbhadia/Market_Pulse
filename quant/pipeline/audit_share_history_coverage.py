"""Certify evidence-only historical shares against the same dated research universe."""
from pathlib import Path
import json
import pandas as pd

from quant.features.share_history import share_history
from quant.pipeline.audit_fundamental_coverage import coverage_dates
from quant.research.coverage_policy import reliable_interval
from quant.storage.parquet_store import read_parquet_file
from quant.storage.research_store import digest_file, write_json


def verify_share_archives(frame, data_dir):
    """A VERIFIED flag and a hash-shaped string do not establish archived evidence."""
    result = frame.copy()
    cache = {}
    for i, row in result.iterrows():
        raw, expected = row.get('raw_path'), row.get('source_sha256')
        path = (data_dir/str(raw)).resolve()
        key = (str(path), expected)
        if key not in cache:
            cache[key] = (isinstance(raw, str) and path.is_relative_to(data_dir.resolve())
                          and path.is_file() and digest_file(path) == expected)
        if not cache[key]:
            result.loc[i, 'verification_status'] = 'NEEDS_REVIEW'
    return result


def audit_share_history_coverage(universe, anchors, events, coverage, sessions, *, start, end):
    if universe.duplicated(['as_of', 'instrument_id']).any():
        raise ValueError('Duplicate dated share-coverage universe')
    rows = []
    for day in coverage_dates(sessions, start, end, 'monthly'):
        cross = universe[pd.to_datetime(universe.as_of).eq(day) & universe.eligible.eq(True)].copy()
        cutoff = day.tz_localize('Asia/Kolkata')+pd.Timedelta(hours=15, minutes=30)
        verified = share_history(anchors, events, coverage,
            cross[['as_of', 'instrument_id']].assign(signal_timestamp=cutoff))
        names = set(verified.loc[verified.value_feature_valid.eq(True), 'instrument_id']) if len(verified) else set()
        liquid = cross.sort_values(['adv60', 'instrument_id'], ascending=[False, True]).head(100)
        count, top = len(cross), len(liquid)
        available = int(cross.instrument_id.isin(names).sum())
        top_available = int(liquid.instrument_id.isin(names).sum())
        overall, top_pct = (100*available/count if count else None), (100*top_available/top if top else None)
        rows.append(dict(as_of=str(day.date()), eligible_count=count,
            eligible_with_verified_shares=available, verified_share_coverage=overall,
            top100_adv_count=top, top100_with_verified_shares=top_available,
            top100_verified_share_coverage=top_pct,
            thresholds_met=bool(count and top and overall >= 80 and top_pct >= 90)))
    reliable = reliable_interval(rows)
    return dict(status='COVERAGE_ESTABLISHED' if reliable else 'NOT_READY', periods=rows,
        first_reliable_share_signal_date=reliable, reliable_window_established=reliable is not None,
        minimum_consecutive_monthly_cutoffs=12, coverage_units='PERCENT',
        value_feature_policy='MISSING_UNLESS_VALUE_FEATURE_VALID_TRUE', current_shares_backfilled=False)


def main():
    from quant.pipeline.cli import parser_config
    parser, config = parser_config(__doc__)
    for name in ('universe', 'anchors', 'capital-events', 'share-coverage'):
        parser.add_argument('--'+name, type=Path, required=True)
    args = parser.parse_args()
    config = args.config(config)
    calendar = read_parquet_file(config.calendar_path)
    paths = [args.universe, args.anchors, args.capital_events, args.share_coverage]
    frames = [read_parquet_file(p) for p in paths]
    frames[1:] = [verify_share_archives(f, config.data_dir) for f in frames[1:]]
    report = audit_share_history_coverage(*frames,
        calendar.loc[calendar.is_trading_session, 'trade_date'], start=args.start, end=args.end)
    report['input_sha256'] = {str(p): digest_file(p) for p in [*paths, config.calendar_path]}
    write_json(config.data_dir/'reports/share-history-coverage.json', report)
    print(json.dumps(report, indent=2))
    return 0 if report['reliable_window_established'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
