"""The dated, evidence-only workload for expanding official filing discovery."""
from collections import Counter

import pandas as pd

from quant.forward.signal_store import content_hash
from quant.pipeline.plan_fundamental_discovery_expansion import plan_discovery_expansion
from quant.features.fundamental_snapshot import evidence_known_times

SOURCE_HIERARCHY = ['NSE_OFFICIAL', 'BSE_OFFICIAL', 'ISSUER_IR']


def build_discovery_gap(universe, coverage, ceiling, filings):
    """One row per discovery gap, distinct from existing acquisition repairs.

    Period requirements are bounds, not fabricated fiscal reporting dates. An
    annual statement or a fresh quarter/YTD can repair the selector's cell;
    complete V2 feature availability remains a separate certification gate.
    """
    plan = plan_discovery_expansion(universe, coverage, ceiling)
    by_name = {str(i): g for i, g in filings.groupby('instrument_id')} if len(filings) else {}
    rows = []
    for target in plan['targets']:
        cutoff = pd.Timestamp(target['latest_permissible_dissemination'])
        candidates = by_name.get(str(target['instrument_id']), filings.iloc[:0])
        known = candidates
        if len(candidates):
            known = candidates[evidence_known_times(candidates, 'exchange_disseminated_at',
                extras=('revision_at', 'available_at')).le(cutoff)]
        urls = known.get('source_document', pd.Series(dtype='string')).astype('string')
        parsed = known.get('parser_status', pd.Series(dtype='string')).eq('PARSED')
        candidate_present, url_present = bool(len(known)), bool(urls.str.startswith('https://', na=False).any())
        entity = target['entity_type']
        if entity == 'UNKNOWN' and len(known):
            classes = known.get('entity_type', pd.Series(dtype=str)).dropna()
            if len(classes) and classes.nunique() == 1:
                entity = str(classes.iloc[0])
            elif 'bank' in known and known.bank.eq(True).any():
                entity = 'BANK'
        rows.append(dict(as_of=target['as_of'], instrument_id=target['instrument_id'],
            symbol=target['symbol'], entity_type=entity, ADV_rank=target['adv_rank'],
            required_period_end=target['requested_period_end_no_later_than'],
            required_period_end_rule='ON_OR_BEFORE_CUTOFF_AND_WITHIN_FRESHNESS_BOUNDS',
            required_period_type='ANNUAL_OR_QUARTER_ONLY_OR_YTD',
            required_statement_basis=coverage.get('basis', 'CONSOLIDATED'),
            freshness_deadline=target['quarter_period_end_no_earlier_than'],
            annual_period_end_no_earlier_than=target['annual_period_end_no_earlier_than'],
            latest_acceptable_dissemination=cutoff.isoformat(),
            filing_present=bool(parsed.any()), candidate_present=candidate_present,
            candidate_url_present=url_present,
            gap_reason='NO_KNOWN_CANDIDATE' if not candidate_present else
                'NO_KNOWN_DOCUMENT_URL' if not url_present else 'NO_PIT_USABLE_CANDIDATE',
            priority=target['priority_rank'], top100=target['top100'],
            consecutive_missing_months=target['consecutive_missing_months'],
            missing_months_for_instrument=0, source_hierarchy=SOURCE_HIERARCHY))
    counts = Counter(r['instrument_id'] for r in rows)
    for row in rows:
        row['missing_months_for_instrument'] = counts[row['instrument_id']]
    thresholds = {r['as_of']: r for r in plan['targets']}
    rows.sort(key=lambda r: (-int(r['top100']),
        thresholds[r['as_of']]['overall_names_to_threshold']+thresholds[r['as_of']]['top100_names_to_threshold'],
        -r['consecutive_missing_months'], -int(any(c in r['entity_type'].upper() for c in ('BANK', 'NBFC'))),
        -r['missing_months_for_instrument'], r['ADV_rank'], r['as_of'], r['instrument_id']))
    for priority, row in enumerate(rows, 1):
        row['priority'] = priority
    return dict(status='DISCOVERY_REQUIRED' if rows else 'NO_DISCOVERY_GAPS',
        cells=rows, missing_cells=len(rows), missing_instruments=len(counts),
        authoritative_workload='DATED_COVERAGE_CEILING_WITHOUT_USABLE_DISCOVERED_CANDIDATE',
        snapshot_expected_cells=6460, snapshot_count_matches=len(rows) == 6460,
        performance_used_to_prioritize=False, coverage_certified=False,
        source_hierarchy=SOURCE_HIERARCHY, ceiling_sha256=content_hash(ceiling),
        input_content_sha256=ceiling['input_content_sha256'],
        sha256=content_hash(rows))


def select_discovery_batch(ledger, *, max_instruments=25, max_cells=100):
    if not 1 <= max_instruments <= 50 or not 1 <= max_cells <= 100:
        raise ValueError('Discovery batches require 1-50 instruments and 1-100 cells')
    if ledger.get('sha256') != content_hash(ledger['cells']):
        raise ValueError('Discovery gap ledger checksum changed')
    selected, names = [], set()
    for row in sorted(ledger['cells'], key=lambda r: r['priority']):
        if row['instrument_id'] not in names and len(names) >= max_instruments:
            continue
        selected.append(row)
        names.add(row['instrument_id'])
        if len(selected) == max_cells:
            break
    return selected
