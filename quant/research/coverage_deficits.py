"""Explain missing PIT coverage without using prices or future returns."""
import math
import pandas as pd
from quant.pipeline.report_fundamental_acquisition import classify_attempt

REASONS = ('unattempted', 'download_failure', 'parser_failure', 'timing_failure',
           'identity_failure', 'unsupported_entity')
FAILURE_REASONS = ('unattempted_document', 'not_discovered', 'download_failure', 'parser_failure',
                   'timing_failure', 'identity_failure', 'unsupported_entity', 'stale_filing')


def candidate_id(row):
    value = row.get('metadata_filing_id')
    return value if isinstance(value, str) and value else row['filing_id']


def coverage_deficits(cross, filings, usable, liquid, cutoff, *, attempts=None,
                      share_validity=None, overall_threshold=80., top_threshold=90.,
                      max_age_days=550, max_quarter_age_days=180):
    attempts = attempts or {}
    missing = cross[~cross.instrument_id.isin(usable)] if len(cross) else cross
    counts = {'missing_'+key: 0 for key in REASONS}
    details = []
    columns = ['instrument_id', 'symbol', 'filing_id', 'metadata_filing_id',
               'exchange_disseminated_at', 'available_at', 'revision_at', 'timing_status', 'document_sha256', 'parser_status',
               'period_start', 'period_end', 'period_type', 'source_document']
    evidence = filings[[c for c in columns if c in filings]].copy()
    if len(evidence):
        from quant.features.fundamental_snapshot import evidence_known_times
        evidence['_known_at'] = evidence_known_times(evidence, 'exchange_disseminated_at',
            extras=('revision_at', 'available_at'))
    by_name = {str(k): v for k, v in evidence.groupby('instrument_id', observed=True)} if len(evidence) else {}
    unresolved = evidence[evidence.instrument_id.isna()] if len(evidence) else evidence
    liquid_names = set(liquid.instrument_id) if len(liquid) else set()
    attribution = dict.fromkeys(FAILURE_REASONS, 0)
    for member in missing.to_dict('records'):
        iid = member['instrument_id']
        candidates = by_name.get(str(iid), evidence.iloc[:0])
        identity = False
        if candidates.empty and len(unresolved) and member.get('symbol') and 'symbol' in unresolved:
            candidates = unresolved[unresolved.symbol.eq(member['symbol'])]
            identity = not candidates.empty
        # Select only disclosures known at the cutoff. Future filings cannot
        # explain an earlier parser failure or become an earlier acquisition gain.
        if len(candidates):
            known = candidates[candidates['_known_at'].le(cutoff)]
        else:
            known = candidates
        reason = 'unattempted'
        if len(candidates) and (known.empty or not known.timing_status.eq('VERIFIED').any()):
            reason = 'timing_failure'
        elif identity:
            reason = 'identity_failure'
        elif len(known):
            row = known.sort_values('exchange_disseminated_at').iloc[-1].to_dict()
            attempt = attempts.get(candidate_id(row)) or attempts.get(row['filing_id'])
            if attempt is None and isinstance(row.get('document_sha256'), str):
                attempt = dict(parser_status=row.get('parser_status'), review=[])
            if attempt:
                status, retry = classify_attempt(attempt)
                reason = ('download_failure' if retry else 'unsupported_entity' if status == 'UNSUPPORTED_ENTITY'
                          else 'parser_failure')
        counts['missing_'+reason] += 1
        canonical = 'unattempted_document' if reason == 'unattempted' else reason
        if candidates.empty:
            canonical = 'not_discovered'
        elif len(known):
            from quant.features.fundamental_snapshot import period_semantics
            fresh = []
            day = pd.Timestamp(cutoff).tz_convert('Asia/Kolkata').tz_localize(None).normalize()
            for item in known.to_dict('records'):
                end = item.get('period_end')
                if end is not None and pd.notna(end):
                    semantics = period_semantics(item.get('period_start'), end, item.get('period_type'))
                    if semantics != 'UNKNOWN':
                        age = (day-pd.Timestamp(end)).days
                        fresh.append(0 <= age <= (max_age_days if semantics == 'ANNUAL' else max_quarter_age_days))
            if fresh and not any(fresh):
                canonical = 'stale_filing'
        attribution[canonical] += 1
        details.append(dict(instrument_id=iid, reason='missing_'+reason, failure_reason=canonical,
            top100=iid in liquid_names,
            candidate_ids=sorted({candidate_id(r) for r in known.to_dict('records')})))
    verified = None
    if share_validity is not None:
        verified = set(share_validity.loc[share_validity.value_feature_valid.eq(True), 'instrument_id'])
    count, top = len(cross), len(liquid)
    available = sum(i in usable for i in cross.instrument_id) if count else 0
    top_available = sum(i in usable for i in liquid.instrument_id) if top else 0
    return dict(**counts, coverage_failure_attribution=attribution,
        missing_share_failure=sum(i not in verified for i in cross.instrument_id) if verified is not None else None,
        share_assessment='ASSESSED' if verified is not None else 'UNASSESSED', missing_details=details,
        overall_gap_to_80=max(0., overall_threshold-100*available/count) if count else None,
        top100_gap_to_90=max(0., top_threshold-100*top_available/top) if top else None,
        overall_missing_names_to_threshold=max(0, math.ceil(count*overall_threshold/100)-available),
        top100_missing_names_to_threshold=max(0, math.ceil(top*top_threshold/100)-top_available))
