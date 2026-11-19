"""An optimistic discovery ceiling is a feasibility estimate, never certification."""
import argparse
import json
from pathlib import Path

import pandas as pd

from quant.features.fundamental_snapshot import fundamental_snapshot
from quant.forward.signal_store import content_hash
from quant.pipeline.report_fundamental_acquisition import classify_attempt
from quant.research.coverage_deficits import candidate_id
from quant.research.coverage_policy import reliable_interval
from quant.storage.parquet_store import read_parquet_file
from quant.storage.research_store import digest_file, write_json


def dated_deficits(universe, coverage):
    """Bind missing identities and liquidity ranks to the original monthly audit."""
    if coverage.get('frequency') != 'monthly' or not coverage.get('periods'):
        raise ValueError('A monthly attributable coverage audit is required')
    if universe.duplicated(['as_of', 'instrument_id']).any():
        raise ValueError('Duplicate dated eligible identities')
    days = [r['as_of'] for r in coverage['periods']]
    if days != sorted(set(days)) or pd.PeriodIndex(days, freq='M').has_duplicates:
        raise ValueError('Monthly cutoffs must be ordered and unique')
    for period in coverage['periods']:
        cross = universe[pd.to_datetime(universe.as_of).eq(period['as_of']) & universe.eligible.eq(True)]
        liquid = cross.dropna(subset=['adv60']).sort_values(
            ['adv60', 'instrument_id'], ascending=[False, True]).head(coverage.get('requested_top_liquidity_count', 100))
        expected = content_hash(cross[['instrument_id', 'adv60']].sort_values('instrument_id').to_dict('records'))
        if (len(cross) != period['eligible_universe_count'] or len(liquid) != period['top_liquidity_count']
                or expected != period.get('universe_sha256')):
            raise ValueError('Coverage audit and dated universe identities, denominators or ADV differ')
        missing = period.get('missing_details', [])
        ids = [r['instrument_id'] for r in missing]
        top = set(liquid.instrument_id)
        if (len(ids) != len(set(ids)) or not set(ids).issubset(set(cross.instrument_id))
                or len(ids) != len(cross)-period['usable_fundamentals_count']
                or sum(i not in ids for i in top) != period['top_liquidity_usable']
                or any(r.get('top100') != (r['instrument_id'] in top) for r in missing)):
            raise ValueError('Missing coverage identities do not reconcile with the audited counts')
        yield period, cross, liquid, missing


def optimistic_candidates(filings, attempts):
    """Simulate successful parsing only in memory; keep bad revisions as blockers."""
    frame = filings.copy()
    if frame.empty:
        return frame
    frame['_candidate_id'] = [candidate_id(r) for r in frame.to_dict('records')]
    if 'first_seen_at' in frame:
        frame = frame.sort_values('first_seen_at')
    frame = frame.drop_duplicates('_candidate_id', keep='last')
    for index, row in frame.iterrows():
        attempt = attempts.get(row['_candidate_id']) or attempts.get(row['filing_id'])
        url = row.get('source_document')
        if (isinstance(url, str) and url.strip()
                and (attempt is None or classify_attempt(attempt)[1])):
            # These placeholders are never written as filings or passed to research.
            frame.loc[index, 'parser_status'] = 'PARSED'
            frame.loc[index, 'document_sha256'] = '0'*64
    return frame


def coverage_ceiling(universe, coverage, filings, *, attempts=None):
    possible = optimistic_candidates(filings, attempts or {})
    rows = []
    overall = coverage.get('universe_threshold_pct', 80.)
    top_threshold = coverage.get('liquidity_threshold_pct', 90.)
    if overall < 80 or top_threshold < 90:
        raise ValueError('Ceilings cannot weaken the 80% / 90% coverage gates')
    for period, cross, liquid, missing in dated_deficits(universe, coverage):
        cutoff = pd.Timestamp(period['as_of'], tz='Asia/Kolkata')+pd.Timedelta(hours=15, minutes=30)
        snapshot = fundamental_snapshot(possible, cutoff, instrument_ids=set(cross.instrument_id),
            basis=coverage.get('basis', 'CONSOLIDATED'), max_age_days=coverage.get('max_age_days', 550),
            max_quarter_age_days=coverage.get('max_quarter_age_days', 180))
        potential = set(snapshot.instrument_id) if len(snapshot) else set()
        details = [dict(r, candidate_document_available=r['instrument_id'] in potential) for r in missing]
        count, top = len(cross), len(liquid)
        current, current_top = period['usable_fundamentals_count'], period['top_liquidity_usable']
        with_candidate = sum(r['candidate_document_available'] for r in details)
        missing_top = [r for r in details if r['top100']]
        top_with_candidate = sum(r['candidate_document_available'] for r in missing_top)
        pct = lambda n, d: 100*n/d if d else None
        passing = bool(count and top and pct(current, count) >= overall and pct(current_top, top) >= top_threshold)
        reachable = bool(count and top and pct(current+with_candidate, count) >= overall
                         and pct(current_top+top_with_candidate, top) >= top_threshold)
        rows.append(dict(as_of=period['as_of'], eligible_count=count, top100_count=top,
            current_usable_count=current, missing_eligible_count=len(details),
            missing_with_candidate_document=with_candidate,
            missing_without_candidate_document=len(details)-with_candidate,
            missing_top100_count=len(missing_top), missing_top100_with_candidate_document=top_with_candidate,
            missing_top100_without_candidate_document=len(missing_top)-top_with_candidate,
            current_coverage=pct(current, count), theoretical_max_coverage=pct(current+with_candidate, count),
            current_top100_coverage=pct(current_top, top),
            theoretical_max_top100_coverage=pct(current_top+top_with_candidate, top),
            theoretical_discovered_coverage=pct(current+with_candidate, count),
            theoretical_discovered_top100_coverage=pct(current_top+top_with_candidate, top),
            gap_to_80=max(0., overall-pct(current, count)) if count else None,
            gap_to_90=max(0., top_threshold-pct(current_top, top)) if top else None,
            missing_cells=len(details), missing_instruments=len({r['instrument_id'] for r in details}),
            classification='ALREADY_PASSING' if passing else 'REACHABLE' if reachable else 'UNREACHABLE_WITH_CURRENT_DISCOVERY',
            thresholds_met=reachable, missing_details=details))
    reliable = reliable_interval(rows)
    return dict(status='THEORETICALLY_REACHABLE' if reliable else 'DISCOVERY_EXPANSION_REQUIRED',
        frequency='monthly', periods=rows, theoretical_reliable_start=reliable,
        universe_threshold_pct=overall, liquidity_threshold_pct=top_threshold,
        minimum_consecutive_monthly_cutoffs=12, coverage_certified=False,
        performance_used_to_prioritize=False,
        assumptions='Every nonterminal URL candidate parses successfully; verified timing, identity, basis, duration, freshness and revision rules still apply',
        input_content_sha256=dict(universe=content_hash(universe[['as_of', 'instrument_id', 'eligible', 'adv60']].to_dict('records')),
                                  coverage=content_hash(coverage)))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('universe', 'coverage', 'filings', 'output'):
        parser.add_argument('--'+name, type=Path, required=True)
    parser.add_argument('--attempts', type=Path)
    args = parser.parse_args()
    report = coverage_ceiling(read_parquet_file(args.universe), json.loads(args.coverage.read_text(encoding='utf-8')),
        read_parquet_file(args.filings), attempts=json.loads(args.attempts.read_text(encoding='utf-8'))['attempted'] if args.attempts else None)
    report['input_sha256'] = {str(p): digest_file(p) for p in (args.universe, args.coverage, args.filings, args.attempts) if p}
    write_json(args.output, report)
    print(json.dumps({k: v for k, v in report.items() if k != 'periods'}, indent=2))


if __name__ == '__main__':
    main()
