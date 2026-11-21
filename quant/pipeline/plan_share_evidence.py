"""Measure verified share coverage and the optimistic ceiling of candidate evidence."""
import json
from collections import Counter
from pathlib import Path

import pandas as pd

from quant.features.share_history import share_history
from quant.features.fundamental_snapshot import evidence_known_times
from quant.pipeline.audit_fundamental_coverage import coverage_dates
from quant.pipeline.audit_share_history_coverage import verify_share_archives
from quant.research.coverage_policy import reliable_interval
from quant.storage.parquet_store import read_parquet_file
from quant.storage.research_store import digest_file, write_json


def candidate_evidence(frame):
    """A reviewable existing source is a candidate; absent evidence is never one."""
    result = frame.copy()
    if not result.empty:
        url = result.get('source', pd.Series('', index=result.index)).astype('string')
        hashed = result.get('source_sha256', pd.Series('', index=result.index)).astype('string').str.fullmatch('[0-9a-f]{64}', na=False)
        possible = result.verification_status.isin(['VERIFIED', 'VERIFIED_COMPLETE', 'TERMS_VERIFIED',
            'DATES_VERIFIED', 'NEEDS_REVIEW', 'CANDIDATE']) & (hashed | url.str.startswith('https://', na=False))
        result.loc[possible, 'verification_status'] = 'VERIFIED_COMPLETE' if 'event_type' in result else 'VERIFIED'
        # Placeholder hashes exist only inside this optimistic calculation.
        result.loc[possible & ~hashed, 'source_sha256'] = '0'*64
    return result


def plan_share_evidence(universe, anchors, events, coverage, sessions, *, start, end, filing_coverage=None):
    if universe.duplicated(['as_of', 'instrument_id']).any():
        raise ValueError('Duplicate dated share-coverage universe')
    possible = [candidate_evidence(f) for f in (anchors, events, coverage)]
    # Bind the hypothetical in-memory inventory to the hypothetical review
    # statuses. Missing completeness facts and unresolved events remain missing.
    from quant.data.capital_events import anchor_hash, event_inventory_hash
    for index, proof in possible[2].iterrows():
        if not all(k in proof and pd.notna(proof[k]) for k in ('interval_start', 'interval_end', 'event_inventory_hash')):
            continue
        known = possible[0][possible[0].instrument_id.eq(proof.instrument_id)]
        known = known[pd.to_datetime(known.effective_date).between(pd.Timestamp(proof.interval_start), pd.Timestamp(proof.interval_end))].sort_values('effective_date')
        if known.effective_date.nunique() >= 2:
            possible[2].loc[index, 'event_inventory_hash'] = event_inventory_hash(possible[1], proof.instrument_id, proof.interval_start, proof.interval_end)
            possible[2].loc[index, 'reconciled_start_anchor'] = anchor_hash(known.iloc[0])
            possible[2].loc[index, 'reconciled_end_anchor'] = anchor_hash(known.iloc[-1])
    periods, targets = [], []
    filing_periods = {r['as_of']: r for r in (filing_coverage or {}).get('periods', [])}
    for day in coverage_dates(sessions, start, end, 'monthly'):
        cross = universe[pd.to_datetime(universe.as_of).eq(day) & universe.eligible.eq(True)]
        liquid = cross.dropna(subset=['adv60']).sort_values(['adv60', 'instrument_id'], ascending=[False, True]).head(100)
        keys = cross[['as_of', 'instrument_id']].assign(signal_timestamp=day.tz_localize('Asia/Kolkata')+pd.Timedelta(hours=15, minutes=30))
        actual = share_history(anchors, events, coverage, keys)
        potential = share_history(*possible, keys)
        names = set(actual.loc[actual.value_feature_valid.eq(True), 'instrument_id']) if len(actual) else set()
        possible_names = set(potential.loc[potential.value_feature_valid.eq(True), 'instrument_id']) if len(potential) else set()
        candidate_anchors = possible[0]
        if len(candidate_anchors):
            cutoff = keys.signal_timestamp.iloc[0] if len(keys) else day.tz_localize('Asia/Kolkata')+pd.Timedelta(hours=15, minutes=30)
            valid_anchors = candidate_anchors[candidate_anchors.verification_status.eq('VERIFIED')
                & evidence_known_times(candidate_anchors, 'exchange_disseminated_at').le(cutoff)
                & pd.to_datetime(candidate_anchors.effective_date).le(day)
                & pd.to_numeric(candidate_anchors.shares_outstanding, errors='coerce').gt(0)]
            anchor_names = set(valid_anchors.instrument_id)
        else:
            anchor_names = set()
        missing = set(cross.instrument_id)-names
        filing_period = filing_periods.get(str(day.date()))
        filing_missing = {r['instrument_id'] for r in filing_period.get('missing_details', [])} if filing_period else None
        count, top = len(cross), len(liquid)
        pct = lambda n, d: 100*n/d if d else None
        current, ceiling = pct(len(names), count), pct(len(names | possible_names), count)
        current_top, ceiling_top = pct(len(set(liquid.instrument_id) & names), top), pct(len(set(liquid.instrument_id) & (names | possible_names)), top)
        passing = bool(count and top and current >= 80 and current_top >= 90)
        reachable = bool(count and top and ceiling >= 80 and ceiling_top >= 90)
        periods.append(dict(as_of=str(day.date()), eligible_count=count, top100_count=top,
            current_verified_share_count=len(names), current_verified_share_coverage=current,
            theoretical_max_verified_share_coverage=ceiling,
            current_top100_share_coverage=current_top, theoretical_max_top100_share_coverage=ceiling_top,
            missing_names_with_candidate_share_evidence=len(missing & anchor_names),
            missing_names_without_candidate_share_evidence=len(missing-anchor_names),
            missing_names_with_candidate_complete_chain=len(missing & possible_names),
            classification='ALREADY_PASSING' if passing else 'REACHABLE' if reachable else 'UNREACHABLE_WITH_CURRENT_DISCOVERY',
            thresholds_met=reachable))
        for rank, row in enumerate(cross.sort_values(['adv60', 'instrument_id'], ascending=[False, True]).to_dict('records'), 1):
            if row['instrument_id'] in missing:
                candidate = row['instrument_id'] in possible_names
                targets.append(dict(as_of=str(day.date()), instrument_id=row['instrument_id'], top100=row['instrument_id'] in set(liquid.instrument_id),
                    usable_pit_filings=row['instrument_id'] not in filing_missing if filing_missing is not None else None,
                    likely_v2_covered_candidate=bool(filing_missing is not None and row['instrument_id'] not in filing_missing
                        and row['instrument_id'] in anchor_names),
                    adv_rank=rank, candidate_chain_available=candidate, candidate_anchor_available=row['instrument_id'] in anchor_names,
                    required_action='VERIFY_ARCHIVED_ANCHOR_AND_EVENT_CHAIN' if candidate else
                        'CERTIFY_COMPLETE_CAPITAL_EVENT_INTERVAL' if row['instrument_id'] in anchor_names else
                        'DISCOVER_DATED_EQUITY_CAPITAL_FACE_VALUE_AND_COMPLETE_CAPITAL_EVENT_INTERVAL'))
    repairs = Counter(r['instrument_id'] for r in targets)
    for row in targets:
        row['monthly_repair_potential'] = repairs[row['instrument_id']]
    targets.sort(key=lambda r: (-int(r['top100']), -int(r['usable_pit_filings'] is True),
        -int(r['likely_v2_covered_candidate']), -r['monthly_repair_potential'], r['adv_rank'], r['as_of'], r['instrument_id']))
    return dict(status='PLANNED', periods=periods, targets=targets,
        theoretical_reliable_start=reliable_interval(periods), coverage_certified=False,
        value_research_enabled=False, current_shares_backfilled=False, performance_used_to_prioritize=False,
        assumptions='Existing candidate anchors, event terms and complete interval evidence all verify; unknown counts and missing intervals remain missing')


def main():
    from quant.pipeline.cli import parser_config
    parser, config = parser_config(__doc__)
    for name in ('universe', 'anchors', 'capital-events', 'share-coverage', 'output'):
        parser.add_argument('--'+name, type=Path, required=True)
    parser.add_argument('--filing-coverage', type=Path)
    args = parser.parse_args()
    config = args.config(config)
    paths = (args.universe, args.anchors, args.capital_events, args.share_coverage, config.calendar_path)
    universe, *frames, calendar = [read_parquet_file(p) for p in paths]
    frames = [verify_share_archives(f, config.data_dir) for f in frames]
    report = plan_share_evidence(universe, *frames, calendar.loc[calendar.is_trading_session, 'trade_date'],
        start=args.start, end=args.end, filing_coverage=json.loads(args.filing_coverage.read_text(encoding='utf-8')) if args.filing_coverage else None)
    report['input_sha256'] = {str(p): digest_file(p) for p in paths}
    if args.filing_coverage:
        report['input_sha256'][str(args.filing_coverage)] = digest_file(args.filing_coverage)
    write_json(args.output, report)
    print(json.dumps({k: v for k, v in report.items() if k not in ('periods', 'targets')}, indent=2))


if __name__ == '__main__':
    main()
