"""Auditable capital changes and reconciliation of historical share intervals."""
import math
import re

import pandas as pd

from quant.features.fundamental_snapshot import evidence_known_times, number_or_nan
from quant.forward.signal_store import content_hash
from quant.version import SHARE_CHAIN_VERSION

EVENT_TYPES = ('SPLIT', 'BONUS', 'BUYBACK', 'RIGHTS_ISSUE', 'PUBLIC_ISSUE',
    'PRIVATE_PLACEMENT', 'ESOP_ISSUANCE', 'MERGER_CONVERSION', 'DEMERGER_ALLOCATION',
    'CAPITAL_REDUCTION', 'FACE_VALUE_CHANGE', 'OTHER')
EVENT_FIELDS = ('instrument_id', 'security_lineage_id', 'event_type', 'announced_at',
    'record_date', 'effective_date', 'share_multiplier', 'shares_added', 'shares_removed',
    'paid_up_capital_before', 'paid_up_capital_after', 'face_value_before', 'face_value_after',
    'source_url', 'source_sha256', 'verification_status')
ALIASES = {'ISSUANCE': 'PUBLIC_ISSUE', 'MERGER': 'MERGER_CONVERSION'}


def present(value):
    return value is not None and not pd.isna(value)


def replay_capital_event(shares, row):
    """Apply disclosed arithmetic; a reported after-count cannot force equality."""
    kind = ALIASES.get(row['event_type'], row['event_type'])
    if kind not in EVENT_TYPES or kind == 'OTHER':
        raise ValueError('Unknown capital event terms')
    values = {k: number_or_nan(row.get(k)) for k in
              ('share_multiplier', 'shares_added', 'shares_removed', 'shares_after')}
    for key in values:
        if present(row.get(key)) and not math.isfinite(values[key]):
            raise ValueError('Nonfinite capital event terms')
    multiplier, added, removed = (values[k] for k in ('share_multiplier', 'shares_added', 'shares_removed'))
    if any(math.isfinite(v) and v < 0 for v in (added, removed)):
        raise ValueError('Share additions and removals must be nonnegative')
    if math.isfinite(multiplier) and multiplier <= 0:
        raise ValueError('Share multiplier must be positive')
    if kind in ('SPLIT', 'BONUS', 'FACE_VALUE_CHANGE') and not math.isfinite(multiplier):
        raise ValueError('A face-value/split/bonus event needs a disclosed share multiplier')
    if kind in ('RIGHTS_ISSUE', 'PUBLIC_ISSUE', 'PRIVATE_PLACEMENT', 'ESOP_ISSUANCE') and not math.isfinite(added):
        raise ValueError('Issuance requires disclosed shares added')
    if kind in ('BUYBACK', 'CAPITAL_REDUCTION') and not math.isfinite(removed):
        raise ValueError('Buyback/reduction requires disclosed shares removed')
    if kind in ('MERGER_CONVERSION', 'DEMERGER_ALLOCATION') and not any(
            math.isfinite(v) for v in (multiplier, added, removed)):
        raise ValueError('Conversion/allocation requires disclosed share arithmetic')
    for when, count in [('before', shares)]:
        capital, face = (number_or_nan(row.get(k+'_'+when)) for k in ('paid_up_capital', 'face_value'))
        if math.isfinite(capital) and math.isfinite(face):
            if capital <= 0 or face <= 0 or not math.isclose(capital/face, count, rel_tol=1e-8, abs_tol=1e-6):
                raise ValueError('Capital event before-count does not reconcile')
    result = shares*(multiplier if math.isfinite(multiplier) else 1.)
    result += added if math.isfinite(added) else 0.
    result -= removed if math.isfinite(removed) else 0.
    if not math.isfinite(result) or result <= 0:
        raise ValueError('Capital event produces invalid shares')
    checks = [values['shares_after']]
    capital, face = (number_or_nan(row.get(k+'_after')) for k in ('paid_up_capital', 'face_value'))
    if math.isfinite(capital) and math.isfinite(face):
        if capital <= 0 or face <= 0:
            raise ValueError('Invalid after-event capital/face value')
        checks.append(capital/face)
    if any(math.isfinite(v) and not math.isclose(result, v, rel_tol=1e-8, abs_tol=1e-6) for v in checks):
        raise ValueError('Capital event after-count does not reconcile')
    return result


def capital_event_ledger(events):
    """Normalize existing evidence without inferring event types from prose."""
    result = events.copy()
    for name in EVENT_FIELDS:
        if name not in result:
            result[name] = pd.Series(None, index=result.index, dtype=object)
    if len(result):
        result['event_type'] = result.event_type.replace(ALIASES)
        result['source_url'] = result.source_url.fillna(result.get('source', pd.Series(index=result.index, dtype=object)))
        ids = []
        for i, row in result.iterrows():
            if row.event_type not in EVENT_TYPES:
                raise ValueError('Unrecognized capital event type')
            if not isinstance(row.instrument_id, str) or not row.instrument_id:
                raise ValueError('Capital event identity is required')
            ids.append(content_hash({k: row.get(k) for k in
                (*EVENT_FIELDS, 'candidate_ex_date', 'original_event_id') if k != 'verification_status'}))
            if (pd.isna(row.effective_date) or pd.isna(row.security_lineage_id) or not row.security_lineage_id
                    or pd.isna(row.announced_at) or pd.Timestamp(row.announced_at).tzinfo is None
                    or not re.fullmatch('[0-9a-f]{64}', str(row.source_sha256))
                    or not isinstance(row.source_url, str) or not row.source_url.startswith('https://')):
                result.loc[i, 'verification_status'] = 'NEEDS_REVIEW'
        result['capital_event_id'] = ids
        result = result.drop_duplicates('capital_event_id')
        if result.duplicated(['instrument_id', 'effective_date']).any():
            # Same-day order is material. A reviewed composite event is required.
            result.loc[result.duplicated(['instrument_id', 'effective_date'], keep=False), 'verification_status'] = 'NEEDS_REVIEW'
    else:
        result['capital_event_id'] = pd.Series(dtype=str)
    return result


def capital_candidates_from_actions(actions):
    """Ex-date announcements are leads, not proof of capital-effective dates.

    Keep the original terms and identity. Listing/credit dates, historical
    dissemination and complete lineage still need independent verification.
    """
    kinds = {'SPLIT': 'SPLIT', 'BONUS': 'BONUS', 'RIGHTS': 'RIGHTS_ISSUE',
             'MERGER': 'MERGER_CONVERSION', 'DEMERGER': 'DEMERGER_ALLOCATION'}
    rows = []
    for row in actions.to_dict('records'):
        if row.get('action_type') not in kinds or not isinstance(row.get('instrument_id'), str):
            continue
        numerator, denominator = (number_or_nan(row.get(k)) for k in ('ratio_numerator', 'ratio_denominator'))
        multiplier = None
        if (row.get('parse_status') == 'PARSED' and math.isfinite(numerator)
                and math.isfinite(denominator) and min(numerator, denominator) > 0):
            if row['action_type'] == 'SPLIT':
                multiplier = numerator/denominator
            elif row['action_type'] == 'BONUS':
                multiplier = 1+numerator/denominator
        rows.append(dict(instrument_id=row['instrument_id'], security_lineage_id=None,
            event_type=kinds[row['action_type']], announced_at=None, record_date=row.get('record_date'),
            effective_date=None, candidate_ex_date=row.get('ex_date'), share_multiplier=multiplier,
            shares_added=None, shares_removed=None, source_url=row.get('source_url'),
            source_sha256=row.get('source_sha256'), verification_status='NEEDS_REVIEW',
            original_event_id=row.get('event_id'), subject=row.get('subject'),
            original_announcement_date=row.get('announcement_date'),
            raw_path=row.get('raw_path'), candidate_only=True,
            required_evidence='CAPITAL_EFFECTIVE_DATE_DISSEMINATION_LINEAGE_AND_COMPLETE_EVENT_INTERVAL'))
    return pd.DataFrame(rows)


def reconcile_share_chain(anchors, events, coverage, instrument_id, cutoff):
    """Require two known anchors, complete event coverage and exact replay.

    Reconciliation evidence becomes available at its latest knowledge timestamp.
    A later discovery may diagnose earlier history but cannot enter earlier PIT
    Value features. A source flag alone cannot certify a single-anchor chain.
    """
    cutoff = pd.Timestamp(cutoff)
    if cutoff.tzinfo is None:
        raise ValueError('Share-chain cutoff requires a timezone')
    invalid = dict(share_chain_status='INCOMPLETE', value_feature_valid=False,
                   share_chain_version=SHARE_CHAIN_VERSION,
                   reason='START_AND_LATER_RECONCILIATION_ANCHORS_REQUIRED',
                   reconciliation_known_at=None, source=[])
    if anchors.empty or coverage.empty:
        return invalid
    day = cutoff.tz_convert('Asia/Kolkata').tz_localize(None).normalize()
    known = anchors[anchors.instrument_id.eq(instrument_id)
        & anchors.verification_status.eq('VERIFIED')
        & evidence_known_times(anchors, 'exchange_disseminated_at').le(cutoff)
        & pd.to_datetime(anchors.effective_date).le(day)].copy()
    known = known.sort_values(['effective_date', 'exchange_disseminated_at'])
    if known.effective_date.nunique() < 2:
        return invalid
    if (known.duplicated(['effective_date', 'exchange_disseminated_at']).any()
            or not known.source_sha256.astype('string').str.fullmatch('[0-9a-f]{64}', na=False).all()):
        return dict(invalid, share_chain_status='BROKEN', reason='AMBIGUOUS_OR_UNVERIFIED_ANCHORS')
    # Keep latest known revision for each anchor date; reconcile every consecutive
    # pair so a later anchor cannot erase an unexplained earlier discontinuity.
    known = known.drop_duplicates('effective_date', keep='last')
    first, last = known.iloc[0], known.iloc[-1]
    lineages = set(known.get('security_lineage_id', pd.Series(dtype=str)).dropna())
    if len(lineages) > 1:
        return dict(invalid, share_chain_status='BROKEN', reason='SECURITY_LINEAGE_MISMATCH')
    proofs = coverage[coverage.instrument_id.eq(instrument_id)
        & coverage.verification_status.eq('VERIFIED')
        & evidence_known_times(coverage, 'known_at').le(cutoff)
        & pd.to_datetime(coverage.covered_from).le(pd.Timestamp(first.effective_date))
        & pd.to_datetime(coverage.covered_through).ge(day)
        & coverage.source_sha256.astype('string').str.fullmatch('[0-9a-f]{64}', na=False)]
    if proofs.empty:
        return dict(invalid, reason='COMPLETE_CAPITAL_EVENT_INTERVAL_REQUIRED')
    proof = proofs.sort_values('known_at').iloc[-1]
    sources = list(known.source_sha256)+[proof.source_sha256]
    knowledge = list(evidence_known_times(known, 'exchange_disseminated_at'))+[pd.Timestamp(proof.known_at)]
    changes = events
    if len(events):
        if events.loc[events.instrument_id.eq(instrument_id), 'effective_date'].isna().any():
            return dict(invalid, share_chain_status='BROKEN', reason='UNDATED_CAPITAL_EVENT')
        changes = events[events.instrument_id.eq(instrument_id)
            & pd.to_datetime(events.effective_date).gt(pd.Timestamp(first.effective_date))
            & pd.to_datetime(events.effective_date).le(day)].sort_values('effective_date')
        if (not changes.verification_status.eq('VERIFIED').all()
                or changes.duplicated('effective_date').any()
                or evidence_known_times(changes, 'announced_at').isna().any()
                or not evidence_known_times(changes, 'announced_at').le(cutoff).all()
                or not changes.source_sha256.astype('string').str.fullmatch('[0-9a-f]{64}', na=False).all()):
            return dict(invalid, share_chain_status='BROKEN', reason='UNVERIFIED_OR_UNORDERED_CAPITAL_EVENT')
        if lineages:
            if len(lineages) != 1 or ('security_lineage_id' in changes and
                    not changes.security_lineage_id.isin(lineages).all()):
                return dict(invalid, share_chain_status='BROKEN', reason='SECURITY_LINEAGE_MISMATCH')
        sources += list(changes.source_sha256)
        knowledge += list(evidence_known_times(changes, 'announced_at'))
        if pd.to_datetime(changes.effective_date).gt(pd.Timestamp(last.effective_date)).any():
            return dict(invalid, reason='LATER_ANCHOR_REQUIRED_AFTER_CAPITAL_EVENT')
    replayed = number_or_nan(first.shares_outstanding)
    if not math.isfinite(replayed) or replayed <= 0:
        return dict(invalid, share_chain_status='BROKEN', reason='INVALID_START_ANCHOR')
    previous = pd.Timestamp(first.effective_date)
    try:
        for anchor in known.iloc[1:].itertuples():
            end = pd.Timestamp(anchor.effective_date)
            part = changes[pd.to_datetime(changes.effective_date).gt(previous)
                & pd.to_datetime(changes.effective_date).le(end)] if len(changes) else changes
            for event in part.to_dict('records'):
                replayed = replay_capital_event(replayed, event)
            reported = number_or_nan(anchor.shares_outstanding)
            if not math.isfinite(reported) or not math.isclose(replayed, reported, rel_tol=1e-8, abs_tol=1e-6):
                return dict(invalid, share_chain_status='BROKEN', reason='UNEXPLAINED_ANCHOR_MISMATCH',
                    replayed_shares=replayed, reported_shares=reported)
            previous = end
    except ValueError as error:
        return dict(invalid, share_chain_status='BROKEN', reason=str(error))
    return dict(share_chain_status='VERIFIED_COMPLETE', value_feature_valid=True,
        share_chain_version=SHARE_CHAIN_VERSION,
        reason='REPLAY_RECONCILED_TO_LATER_REPORTED_ANCHOR', shares_outstanding=replayed,
        starting_anchor_date=str(pd.Timestamp(first.effective_date).date()),
        reconciliation_anchor_date=str(pd.Timestamp(last.effective_date).date()),
        reconciliation_known_at=max(knowledge).isoformat(), source=sorted(set(sources)))
