"""Measure historical PIT financial coverage against the dated eligible universe."""
from datetime import date
import json
from pathlib import Path

import pandas as pd

from quant.features.fundamental_snapshot import fundamental_snapshot, SNAPSHOT_VERSION
from quant.storage.parquet_store import read_parquet_file, write_parquet
from quant.storage.research_store import digest_file, write_json


def coverage_dates(sessions, start, end, frequency):
    from quant.universe.eligible import session_index
    dates = session_index(sessions)
    dates = dates[(dates >= pd.Timestamp(start)) & (dates <= pd.Timestamp(end))]
    groups = pd.Series(dates, index=dates).groupby(dates.to_period('M' if frequency == 'monthly' else 'Q'))
    return [pd.Timestamp(group.iloc[-1]) for _, group in groups]


def historical_coverage_universe(prices, sessions, start, end, *, frequency='monthly', lifecycle_events=None):
    """Compute the unchanged daily universe, retaining only coverage-date rows.

    Eligibility keeps its full warmup; no current constituent list is projected
    backward. Compact outputs avoid materializing millions of unused daily rows.
    """
    from quant.universe.eligible import panels, eligibility
    from quant.lifecycle.state import overlay_universe
    cutoffs = coverage_dates(sessions, start, end, frequency)
    rows = []
    for panel in panels(prices, sessions):
        selected = panel.observed & panel.index.isin(cutoffs)
        if selected.any():
            rows.append(eligibility(panel).loc[selected].reset_index())
    if not rows:
        return pd.DataFrame()
    return overlay_universe(pd.concat(rows, ignore_index=True), lifecycle_events)


def verify_filing_archives(filings, data_dir):
    """A parser flag does not prove that original document bytes remain available."""
    frame = filings.copy()
    if frame.empty:
        return frame
    cache = {}
    for i, row in frame.iterrows():
        valid = True
        for path_key, hash_key in [('metadata_raw_path', 'source_sha256'), ('document_raw_path', 'document_sha256')]:
            value, expected = row.get(path_key), row.get(hash_key)
            if not isinstance(value, str) or not isinstance(expected, str):
                valid = False
                break
            path = Path(value)
            path = path if path.is_absolute() else data_dir/path
            if not path.resolve().is_relative_to(data_dir.resolve()):
                valid = False
                break
            key = (str(path), expected)
            if key not in cache:
                cache[key] = path.is_file() and digest_file(path) == expected
            valid &= cache[key]
        if not valid:
            frame.loc[i, 'parser_status'] = 'NEEDS_REVIEW'
    return frame


def audit_fundamental_coverage(universe, filings, sessions, *, start, end, frequency='monthly',
                                top_liquidity_count=100, basis='CONSOLIDATED', max_age_days=550,
                                max_quarter_age_days=180,
                                universe_threshold=80., liquidity_threshold=90., attempts=None,
                                share_validity=None):
    if (frequency not in ('monthly', 'quarterly') or top_liquidity_count < 1
            or not 0 <= universe_threshold <= 100 or not 0 <= liquidity_threshold <= 100):
        raise ValueError('Invalid coverage policy')
    # Include the current partial month, explicitly dated to its last completed session.
    cutoffs = coverage_dates(sessions, start, end, frequency)
    frame = universe.copy()
    if not frame.empty:
        frame['as_of'] = pd.to_datetime(frame.as_of)
        if frame.duplicated(['as_of', 'instrument_id']).any():
            raise ValueError('Duplicate dated universe identities')
    rows = []
    for day in cutoffs:
        cross = frame[frame.as_of.eq(day) & frame.eligible.eq(True)].copy() if not frame.empty else frame
        cutoff = day.tz_localize('Asia/Kolkata')+pd.Timedelta(hours=15, minutes=30)
        snapshot = fundamental_snapshot(filings, cutoff, instrument_ids=set(cross.instrument_id) if not cross.empty else set(),
            basis=basis, max_age_days=max_age_days, max_quarter_age_days=max_quarter_age_days)
        usable = set(snapshot.instrument_id) if not snapshot.empty else set()
        count = len(cross)
        available = int(cross.instrument_id.isin(usable).sum()) if count else 0
        if count and 'adv60' not in cross:
            raise ValueError('Historical ADV is required for liquidity coverage')
        liquid = cross.dropna(subset=['adv60']).sort_values(['adv60', 'instrument_id'], ascending=[False, True]).head(top_liquidity_count) if count else cross
        liquid_usable = int(liquid.instrument_id.isin(usable).sum()) if len(liquid) else 0
        row = dict(as_of=str(day.date()), signal_timestamp=cutoff.isoformat(), eligible_universe_count=count,
            usable_fundamentals_count=available, coverage_pct=100*available/count if count else None,
            top_liquidity_count=len(liquid), top_liquidity_usable=liquid_usable,
            top_liquidity_coverage_pct=100*liquid_usable/len(liquid) if len(liquid) else None,
            universe_assessment='ASSESSED' if count else 'UNASSESSED_EMPTY_OR_MISSING_UNIVERSE')
        from quant.forward.signal_store import content_hash
        row['universe_sha256'] = content_hash(cross[['instrument_id', 'adv60']].sort_values('instrument_id').to_dict('records')) if count else content_hash([])
        # Categories come only from classifications known at this historical date.
        for category in ('bank', 'industrial', 'nbfc'):
            members = cross[cross.entity_type.eq(category)] if count and 'entity_type' in cross else cross.iloc[:0]
            n = len(members)
            n_usable = int(members.instrument_id.isin(usable).sum()) if n else 0
            row[category+'_count'] = n
            row[category+'_usable'] = n_usable
            row[category+'_coverage'] = 100*n_usable/n if n else None
        row['classification_status'] = 'ASSESSED' if count and 'entity_type' in cross and cross.entity_type.isin(['bank','industrial','nbfc']).all() else 'PARTIAL_OR_UNASSESSED'
        row['thresholds_met'] = bool(count and len(liquid) and row['coverage_pct'] >= universe_threshold
                                      and row['top_liquidity_coverage_pct'] >= liquidity_threshold)
        from quant.research.coverage_deficits import coverage_deficits
        shares = (share_validity[pd.to_datetime(share_validity.as_of).eq(day)]
                  if share_validity is not None else None)
        row.update(coverage_deficits(cross, filings, usable, liquid, cutoff, attempts=attempts,
            share_validity=shares, overall_threshold=universe_threshold, top_threshold=liquidity_threshold))
        rows.append(row)
    from quant.research.coverage_policy import reliable_interval
    reliable = reliable_interval(rows) if frequency == 'monthly' else None
    return dict(snapshot_version=SNAPSHOT_VERSION, basis=basis, max_age_days=max_age_days,
        max_quarter_age_days=max_quarter_age_days, frequency=frequency,
        usability_policy='PARSED_KNOWN_REVISION_WITH_VERIFIED_TIMING_IDENTITY_DURATION_BASIS_AND_ARCHIVED_SHA256',
        usability_scope='At least one parsed schema fact; downstream V2 feature completeness is a separate gate',
        requested_top_liquidity_count=top_liquidity_count,
        universe_threshold_pct=universe_threshold, liquidity_threshold_pct=liquidity_threshold,
        first_reliable_fundamental_signal_date=reliable,
        reliable_window_rule='AT_LEAST_12_CONSECUTIVE_MONTHLY_CUTOFFS_AND_ALL_SUBSEQUENT_CUTOFFS_PASS',
        minimum_consecutive_monthly_cutoffs=12,
        coverage_gap_units='PERCENTAGE_POINTS',
        reliable_window_established=reliable is not None, fundamental_scoring_enabled=False,
        status='COVERAGE_ESTABLISHED' if reliable else 'NOT_READY', periods=rows)


def main():
    from quant.pipeline.cli import parser_config
    from quant.storage.duckdb_store import dataset_files
    parser, config = parser_config(__doc__)
    parser.add_argument('--universe', type=Path, help='Dated eligible-universe Parquet; generated from historical bars if omitted')
    parser.add_argument('--frequency', choices=['monthly', 'quarterly'], default='monthly')
    parser.add_argument('--top-liquidity-count', type=int, default=100)
    parser.add_argument('--basis', choices=['CONSOLIDATED', 'STANDALONE'], default='CONSOLIDATED')
    parser.add_argument('--max-age-days', type=int, default=550)
    parser.add_argument('--max-quarter-age-days', type=int, default=180)
    parser.add_argument('--attempts', type=Path, help='Document acquisition checkpoint')
    parser.add_argument('--share-validity', type=Path, help='Dated verified share-feature rows')
    args = parser.parse_args()
    config = args.config(config)
    from quant.storage.research_store import load_research_data
    from quant.pipeline.check_research_ready import require_research_ready
    require_research_ready(config, args.end, args.start)
    if args.universe:
        universe = read_parquet_file(args.universe)
    else:
        from quant.pipeline.backfill_lifecycle import load_lifecycle
        prices, _, sessions, _, _ = load_research_data(config, args.end)
        universe = historical_coverage_universe(prices,sessions,args.start,args.end,
            frequency=args.frequency,lifecycle_events=load_lifecycle(config))
    calendar = read_parquet_file(config.calendar_path)
    sessions = calendar.loc[calendar.is_trading_session, 'trade_date']
    files = dataset_files(config.data_dir, 'financials')
    filings = pd.concat([read_parquet_file(path) for path in files], ignore_index=True) if files else pd.DataFrame()
    filings = verify_filing_archives(filings, config.data_dir)
    report = audit_fundamental_coverage(universe, filings, sessions, start=args.start, end=args.end,
        frequency=args.frequency, top_liquidity_count=args.top_liquidity_count, basis=args.basis,
        max_age_days=args.max_age_days, max_quarter_age_days=args.max_quarter_age_days,
        attempts=json.loads(args.attempts.read_text(encoding='utf-8'))['attempted'] if args.attempts else None,
        share_validity=read_parquet_file(args.share_validity) if args.share_validity else None)
    from quant.universe.config import UniverseConfig
    from quant.storage.research_store import clean_json
    report['input_provenance'] = dict(calendar_sha256=digest_file(config.calendar_path),
        universe_file_sha256=digest_file(args.universe) if args.universe else None,
        universe_source=str(args.universe) if args.universe else 'HISTORICAL_ADJUSTED_BARS_WITH_PIT_LIFECYCLE',
        universe_settings=clean_json(UniverseConfig()),
        financial_files={str(Path(path).relative_to(config.data_dir)):digest_file(path) for path in files},
        attempts_sha256=digest_file(args.attempts) if args.attempts else None,
        share_validity_sha256=digest_file(args.share_validity) if args.share_validity else None)
    write_json(config.data_dir/'reports/fundamental-universe-coverage.json', report)
    write_parquet(pd.DataFrame(report['periods']), config.data_dir/'reports/fundamental-universe-coverage.parquet')
    print(json.dumps({k: v for k, v in report.items() if k != 'periods'}, indent=2))
    return 0 if report['reliable_window_established'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
