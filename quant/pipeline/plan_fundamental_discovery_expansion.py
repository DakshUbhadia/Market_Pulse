"""Target only dated identity gaps that prevent coverage certification."""
import argparse
from collections import Counter, defaultdict
import json
import math
from pathlib import Path

import pandas as pd

from quant.forward.signal_store import content_hash
from quant.pipeline.report_fundamental_coverage_ceiling import dated_deficits
from quant.storage.parquet_store import read_parquet_file
from quant.storage.research_store import digest_file, write_json


def plan_discovery_expansion(universe, coverage, ceiling):
    expected = dict(universe=content_hash(universe[['as_of', 'instrument_id', 'eligible', 'adv60']].to_dict('records')),
                    coverage=content_hash(coverage))
    if ceiling.get('input_content_sha256') != expected:
        raise ValueError('Coverage ceiling is stale; recompute it from the same audit and universe')
    ceilings = {r['as_of']: r for r in ceiling['periods']}
    cells, by_name = [], defaultdict(list)
    for period, cross, liquid, missing in dated_deficits(universe, coverage):
        row = ceilings[period['as_of']]
        if row['classification'] != 'UNREACHABLE_WITH_CURRENT_DISCOVERY':
            continue
        overall_gap = max(0, math.ceil(len(cross)*ceiling['universe_threshold_pct']/100)
                          -round(len(cross)*row['theoretical_max_coverage']/100)) if len(cross) else 0
        top_gap = max(0, math.ceil(len(liquid)*ceiling['liquidity_threshold_pct']/100)
                      -round(len(liquid)*row['theoretical_max_top100_coverage']/100)) if len(liquid) else 0
        members = {r['instrument_id']: r for r in cross.sort_values(
            ['adv60', 'instrument_id'], ascending=[False, True]).to_dict('records')}
        ranks = {iid: i for i, iid in enumerate(members, 1)}
        for detail in row['missing_details']:
            if detail['candidate_document_available'] or not (overall_gap or (top_gap and detail['top100'])):
                continue
            member = members[detail['instrument_id']]
            cell = dict(as_of=period['as_of'], instrument_id=detail['instrument_id'],
                symbol=member.get('symbol'), top100=detail['top100'], adv_rank=ranks[detail['instrument_id']],
                entity_type=member.get('entity_type', 'UNKNOWN'),
                overall_names_to_threshold=overall_gap, top100_names_to_threshold=top_gap,
                latest_permissible_dissemination=period.get('signal_timestamp'),
                requested_period_end_no_later_than=period['as_of'],
                annual_period_end_no_earlier_than=str((pd.Timestamp(period['as_of'])-pd.Timedelta(days=coverage.get('max_age_days', 550))).date()),
                quarter_period_end_no_earlier_than=str((pd.Timestamp(period['as_of'])-pd.Timedelta(days=coverage.get('max_quarter_age_days', 180))).date()),
                requested_facts=['verified dissemination timestamp', 'consolidated period financial statements'],
                routes=['NSE_OFFICIAL', 'BSE_OFFICIAL', 'ISSUER_IR'])
            cells.append(cell)
            by_name[cell['instrument_id']].append(pd.Period(cell['as_of'], freq='M').ordinal)
    longest = {}
    for iid, months in by_name.items():
        run = best = 0
        previous = None
        for month in sorted(months):
            run = run+1 if previous is not None and month == previous+1 else 1
            best, previous = max(best, run), month
        longest[iid] = best
    for cell in cells:
        cell['consecutive_missing_months'] = longest[cell['instrument_id']]
        cell['missing_months_for_instrument'] = len(by_name[cell['instrument_id']])
    cells.sort(key=lambda c: (-int(c['top100']), c['overall_names_to_threshold']+c['top100_names_to_threshold'],
        -c['consecutive_missing_months'], -int(any(x in str(c['entity_type']).upper() for x in ('BANK', 'NBFC'))),
        -c['missing_months_for_instrument'], c['adv_rank'], c['as_of'], c['instrument_id']))
    for rank, cell in enumerate(cells, 1):
        cell['priority_rank'] = rank
    return dict(status='TARGETED_DISCOVERY_REQUIRED' if cells else 'NO_TARGETED_GAPS',
        performance_used_to_prioritize=False, coverage_certified=False, targets=cells,
        target_name_months=len(cells), target_names=len(by_name),
        by_month=dict(Counter(c['as_of'] for c in cells)), ceiling_sha256=content_hash(ceiling))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('universe', 'coverage', 'ceiling', 'output'):
        parser.add_argument('--'+name, type=Path, required=True)
    args = parser.parse_args()
    report = plan_discovery_expansion(read_parquet_file(args.universe),
        json.loads(args.coverage.read_text(encoding='utf-8')), json.loads(args.ceiling.read_text(encoding='utf-8')))
    report['input_sha256'] = {str(p): digest_file(p) for p in (args.universe, args.coverage, args.ceiling)}
    write_json(args.output, report)
    print(json.dumps({k: v for k, v in report.items() if k != 'targets'}, indent=2))


if __name__ == '__main__':
    main()
