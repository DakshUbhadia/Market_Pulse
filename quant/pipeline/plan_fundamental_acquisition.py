"""Rank missing disclosures by potential marginal PIT coverage, never returns."""
from collections import defaultdict
import heapq
import json
from pathlib import Path
import pandas as pd

from quant.features.fundamental_snapshot import normalize_periods
from quant.forward.signal_store import content_hash
from quant.pipeline.report_fundamental_acquisition import classify_attempt
from quant.research.coverage_deficits import candidate_id
from quant.storage.parquet_store import read_parquet_file
from quant.storage.research_store import digest_file, write_json


def acquisition_state_hash(filings, attempts):
    columns = ('filing_id', 'metadata_filing_id', 'instrument_id', 'source_document', 'timing_status',
               'standalone_or_consolidated', 'period_start', 'period_end', 'period_type',
               'exchange_disseminated_at', 'revision_at', 'available_at', 'document_revision_detected_at',
               'parser_status', 'document_sha256')
    rows = filings.reindex(columns=columns).astype('string').fillna('').drop_duplicates()
    rows = rows.sort_values(list(columns)).to_dict('records')
    return content_hash(dict(filings=rows, attempts=attempts))


def plan_acquisition(universe, coverage, filings, *, attempts=None):
    attempts = attempts or {}
    if universe.duplicated(['as_of', 'instrument_id']).any():
        raise ValueError('Planner requires unique dated eligible identities')
    periods = {r['as_of']: r for r in coverage['periods']}
    if coverage.get('frequency') != 'monthly' or not periods:
        raise ValueError('A monthly coverage audit is required')
    cells, liquidity = {}, {}
    for day, period in periods.items():
        cross = universe[pd.to_datetime(universe.as_of).eq(day) & universe.eligible.eq(True)]
        liquid = cross.dropna(subset=['adv60']).sort_values(['adv60', 'instrument_id'], ascending=[False, True]).head(100)
        if len(cross) != period['eligible_universe_count'] or len(liquid) != period['top_liquidity_count']:
            raise ValueError('Coverage audit and dated universe denominators differ')
        if period.get('universe_sha256') != content_hash(cross[['instrument_id', 'adv60']].sort_values('instrument_id').to_dict('records')):
            raise ValueError('Coverage audit and dated universe identities or ADV differ')
        missing = period.get('missing_details')
        if missing is None or len(missing) != len(cross)-period['usable_fundamentals_count']:
            raise ValueError('An attributable coverage audit is required')
        for row in missing:
            iid = row['instrument_id']
            if iid not in set(cross.instrument_id):
                raise ValueError('Coverage deficit is outside the dated eligible universe')
            cells[(day, iid)] = dict(top=iid in set(liquid.instrument_id),
                near=1/(1+period['overall_missing_names_to_threshold']))
        for rank, row in enumerate(cross.sort_values(['adv60', 'instrument_id'], ascending=[False, True]).itertuples(), 1):
            liquidity[(day, row.instrument_id)] = rank
    by_name = defaultdict(list)
    for cell in cells:
        by_name[cell[1]].append(cell)
    candidates = []
    columns = ('filing_id', 'metadata_filing_id', 'instrument_id', 'source_document', 'timing_status',
               'standalone_or_consolidated', 'period_start', 'period_end', 'period_type',
               'exchange_disseminated_at', 'revision_at', 'available_at', 'entity_type', 'financial_schema',
               'document_revision_detected_at', 'first_seen_at')
    frame = normalize_periods(filings[[c for c in columns if c in filings]])
    if len(frame):
        frame['_candidate_id'] = [candidate_id(r) for r in frame.to_dict('records')]
        if 'first_seen_at' in frame:
            frame = frame.sort_values('first_seen_at')
        frame = frame.drop_duplicates('_candidate_id', keep='last')
        from quant.features.fundamental_snapshot import aware_times
        stamps = [aware_times(frame[k]) for k in ('exchange_disseminated_at', 'revision_at', 'available_at') if k in frame]
        frame['_known_at'] = pd.concat(stamps, axis=1).max(axis=1)
    period_keys = ['instrument_id', 'period_start', 'period_end', 'basis', 'period_semantics']
    histories = ({key: group for key, group in frame.groupby(period_keys, dropna=False, observed=True)}
                 if len(frame) else {})
    for row in frame.to_dict('records'):
        key, iid = row['_candidate_id'], row.get('instrument_id')
        attempt = attempts.get(key) or attempts.get(row['filing_id'])
        if attempt and not classify_attempt(attempt)[1]:
            continue
        url = row.get('source_document')
        if not isinstance(url, str) or not url.strip() or row.get('timing_status') != 'VERIFIED':
            continue
        if row['basis'] != coverage.get('basis', 'CONSOLIDATED') or row['period_semantics'] == 'UNKNOWN':
            continue
        stamps = [row.get(k) for k in ('exchange_disseminated_at', 'revision_at', 'available_at')]
        present = [pd.Timestamp(v) for v in stamps if pd.notna(v)]
        if not present or any(s.tzinfo is None for s in present):
            continue
        known = max(present)
        end = pd.Timestamp(row['period_end'])
        repairs = set()
        for cell in by_name.get(iid, []):
            day = pd.Timestamp(cell[0])
            cutoff = day.tz_localize('Asia/Kolkata')+pd.Timedelta(hours=15, minutes=30)
            age = (day-end).days
            limit = coverage.get('max_age_days', 550) if row['period_semantics'] == 'ANNUAL' else coverage.get('max_quarter_age_days', 180)
            history = histories[tuple(row[k] for k in period_keys)]
            latest = history[history._known_at.le(cutoff)]
            current = (not latest.empty and known == latest._known_at.max()
                       and latest.loc[latest._known_at.eq(known), '_candidate_id'].nunique() == 1)
            detected = row.get('document_revision_detected_at')
            revoked = pd.notna(detected) and pd.Timestamp(detected) <= cutoff
            if current and not revoked and known <= cutoff and 0 <= age <= limit:
                repairs.add(cell)
        if repairs:
            candidates.append(dict(filing_id=key, instrument_id=iid, source_document=url,
                entity_type=str(row.get('entity_type') or row.get('financial_schema') or 'UNKNOWN'),
                repair_cells=repairs))
    claimed, top_claimed, selected = set(), defaultdict(int), []

    def score(candidate):
        remaining = candidate['repair_cells']-claimed
        top = sum(cells[c]['top'] and top_claimed[c[0]] < periods[c[0]]['top100_missing_names_to_threshold'] for c in remaining)
        near = sum(cells[c]['near'] for c in remaining)
        months = sorted(pd.Period(c[0], freq='M').ordinal for c in remaining)
        longest = run = 0
        previous = None
        for month in months:
            run = run+1 if previous is not None and month == previous+1 else 1
            longest, previous = max(longest, run), month
        bank = int(any(x in candidate['entity_type'].upper() for x in ('BANK', 'NBFC')))
        return (top, near, longest, bank, len(remaining))

    queue = [((*(-x for x in score(c)), c['filing_id']), i) for i, c in enumerate(candidates)]
    heapq.heapify(queue)
    while queue:
        old, index = heapq.heappop(queue)
        candidate = candidates[index]
        current = (*(-x for x in score(candidate)), candidate['filing_id'])
        if old != current:
            heapq.heappush(queue, (current, index))
            continue
        remaining = candidate['repair_cells']-claimed
        if not remaining:
            continue
        for cell in remaining:
            if cells[cell]['top']:
                top_claimed[cell[0]] += 1
        claimed.update(remaining)
        selected.append(dict(**{k: v for k, v in candidate.items() if k != 'repair_cells'},
            priority_rank=len(selected)+1, potential_marginal_name_months=len(remaining),
            potential_top100_repairs=-current[0], repair_months=sorted(c[0] for c in remaining),
            adv_ranks={c[0]: liquidity[c] for c in remaining}))
    report = dict(status='PLANNED', method='GREEDY_MARGINAL_NAME_MONTH_COVERAGE',
        acquisition_state_sha256=acquisition_state_hash(filings, attempts),
        performance_used_to_prioritize=False, gains_are_estimates_not_certification=True,
        candidate_count=len(selected), candidates=selected,
        deficit_name_months=len(cells), potentially_addressed_name_months=len(claimed),
        unaddressed_name_months=len(cells)-len(claimed))
    report['sha256'] = content_hash(report)
    return report


def load_plan(path):
    report = json.loads(Path(path).read_text(encoding='utf-8'))
    if (report.get('sha256') != content_hash({k: v for k, v in report.items() if k != 'sha256'})
            or report.get('performance_used_to_prioritize') is not False):
        raise ValueError('Acquisition plan checksum or evidence-only policy changed')
    for filename, expected in report.get('input_sha256', {}).items():
        source = Path(filename)
        if not source.is_file() or digest_file(source) != expected:
            raise ValueError('Acquisition plan inputs changed; audit coverage and rebuild the plan')
    return report


def main():
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('universe', 'coverage', 'filings', 'output'):
        parser.add_argument('--'+name, type=Path, required=True)
    parser.add_argument('--attempts', type=Path)
    args = parser.parse_args()
    report = plan_acquisition(read_parquet_file(args.universe),
        json.loads(args.coverage.read_text(encoding='utf-8')), read_parquet_file(args.filings),
        attempts=json.loads(args.attempts.read_text(encoding='utf-8'))['attempted'] if args.attempts else None)
    paths = [args.universe, args.coverage, args.filings, *([args.attempts] if args.attempts else [])]
    report['input_sha256'] = {str(p): digest_file(p) for p in paths}
    report['sha256'] = content_hash({k: v for k, v in report.items() if k != 'sha256'})
    write_json(args.output, report)
    print(json.dumps({k: v for k, v in report.items() if k != 'candidates'}, indent=2))


if __name__ == '__main__':
    main()
