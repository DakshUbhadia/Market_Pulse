"""Evidence-only PIT financial snapshots. No V2 scores or current-share backfills."""
import numpy as np
import pandas as pd

from quant.version import FUNDAMENTAL_SNAPSHOT_VERSION as SNAPSHOT_VERSION


def aware_times(values):
    return pd.to_datetime(values.map(lambda value: value if pd.notna(value)
        and pd.Timestamp(value).tzinfo else pd.NaT), utc=True)


def evidence_known_times(frame, primary, extras=('known_at',)):
    """Knowledge is the latest disclosed timestamp, never a naive wall clock."""
    stamps = [aware_times(frame[primary])]
    valid = stamps[0].notna()
    for key in extras:
        if key in frame:
            parsed = aware_times(frame[key])
            valid &= frame[key].isna() | parsed.notna()
            stamps.append(parsed)
    return pd.concat(stamps, axis=1).max(axis=1).where(valid)


def number_or_nan(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return np.nan


def period_semantics(start, end, declared=None):
    """Classify duration from the actual interval; a 'Quarterly' form can be YTD."""
    if pd.isna(start) or pd.isna(end):
        return 'UNKNOWN'
    days = (pd.Timestamp(end) - pd.Timestamp(start)).days + 1
    if isinstance(declared, str) and declared.lower() == 'annual' and not 350 <= days <= 380:
        return 'UNKNOWN'
    if 80 <= days <= 100:
        return 'QUARTER_ONLY'
    if 350 <= days <= 380:
        return 'ANNUAL'
    if 160 <= days <= 290:
        return 'YTD'
    return 'UNKNOWN'


def normalize_periods(filings):
    frame = filings.copy()
    if frame.empty:
        return frame
    frame['period_semantics'] = [period_semantics(row.get('period_start'), row.get('period_end'), row.get('period_type'))
                                 for row in frame.to_dict('records')]
    basis = frame.standalone_or_consolidated.astype('string').str.lower()
    frame['basis'] = basis.map({'consolidated': 'CONSOLIDATED', 'standalone': 'STANDALONE',
                               'non-consolidated': 'STANDALONE'}).fillna('UNKNOWN')
    return frame


def fundamental_snapshot(filings, signal_timestamp, *, instrument_ids=None, basis='CONSOLIDATED',
                         max_age_days=550, max_quarter_age_days=180):
    """Latest *known* revision per period, then usability. A bad revision revokes use.

    Preserve annual/YTD/quarter durations separately. Never rank revisions by
    download time or mix standalone and consolidated statements.
    """
    cutoff = pd.Timestamp(signal_timestamp)
    if cutoff.tzinfo is None:
        raise ValueError('signal_timestamp requires an explicit timezone')
    if basis not in ('CONSOLIDATED', 'STANDALONE') or max_age_days <= 0 or max_quarter_age_days <= 0:
        raise ValueError('Invalid financial snapshot basis or freshness window')
    if filings.empty:
        return filings.copy()
    frame = normalize_periods(filings)
    def times(name):
        values = frame.get(name, pd.Series(pd.NaT, index=frame.index))
        # A naive wall clock is not verified dissemination evidence.
        return aware_times(values)
    disseminated = times('exchange_disseminated_at')
    revision = times('revision_at')
    available = times('available_at')
    frame['_known_at'] = pd.concat([disseminated, revision, available], axis=1).max(axis=1)
    end = pd.to_datetime(frame.period_end)
    day = cutoff.tz_convert('Asia/Kolkata').tz_localize(None).normalize()
    valid = (frame.timing_status.eq('VERIFIED') & disseminated.notna() & disseminated.le(cutoff)
             & frame._known_at.le(cutoff) & end.le(day) & end.ge(day-pd.Timedelta(days=max_age_days))
             & frame.instrument_id.notna() & frame.basis.eq(basis) & frame.period_semantics.ne('UNKNOWN'))
    valid &= frame.period_semantics.eq('ANNUAL') | end.ge(day-pd.Timedelta(days=max_quarter_age_days))
    for name, parsed in [('revision_at', revision), ('available_at', available)]:
        if name in frame:
            valid &= frame[name].isna() | parsed.notna()
    if 'document_revision_detected_at' in frame:
        detected = pd.to_datetime(frame.document_revision_detected_at, utc=True)
        revoked = frame.loc[detected.le(cutoff), 'metadata_filing_id'].dropna()
        metadata_ids = frame.get('metadata_filing_id', frame.filing_id).fillna(frame.filing_id)
        valid &= ~metadata_ids.isin(revoked)
    if instrument_ids is not None:
        valid &= frame.instrument_id.isin(instrument_ids)
    frame = frame[valid].copy()
    keys = ['instrument_id', 'period_start', 'period_end', 'basis', 'period_semantics']
    # Discovery metadata and its subsequently parsed document represent one
    # disclosure, not two competing revisions. Only discard the document-less
    # representation when the same metadata identity, period and known-at time
    # have an actual document. Different documents remain ambiguity candidates.
    frame['_metadata_id'] = frame.get('metadata_filing_id', frame.filing_id).fillna(frame.filing_id)
    frame['_has_document'] = frame.get('document_sha256', pd.Series('', index=frame.index)).astype('string').str.fullmatch('[0-9a-f]{64}', na=False)
    has_document = frame.groupby(keys+['_known_at', '_metadata_id'], dropna=False)._has_document.transform('any')
    frame = frame[frame._has_document | ~has_document].drop(columns=['_metadata_id', '_has_document'])
    frame = frame.drop_duplicates('filing_id').sort_values(['_known_at', 'filing_id'])
    # Conflicting same-time revisions cannot be ordered by an arbitrary hash.
    ambiguous = frame.duplicated(keys+['_known_at'], keep=False)
    frame['_ambiguous'] = ambiguous
    frame = frame.drop_duplicates(keys, keep='last')
    usable = (frame.parser_status.eq('PARSED') & ~frame._ambiguous
              & frame.get('document_sha256', pd.Series('', index=frame.index)).astype('string').str.fullmatch('[0-9a-f]{64}', na=False))
    return frame[usable].drop(columns=['_known_at', '_ambiguous']).reset_index(drop=True)


def quarter_only_values(snapshot, fields):
    """Derive quarters by differencing comparable cumulative statements only.

    Missing earlier cumulative values leave nulls. Q1 already has quarter-only
    semantics; annual minus nine-month YTD yields Q4. No YTD summation occurs.
    """
    additive = {'revenue', 'other_income', 'operating_profit', 'ebitda', 'ebit', 'finance_cost',
                'pbt', 'tax', 'pat', 'operating_cash_flow', 'capex', 'interest_income',
                'interest_expense', 'net_interest_income', 'provisions'}
    if not set(fields).issubset(additive):
        raise ValueError('Quarter differencing requires additive flow fields; stocks and ratios are excluded')
    frame = snapshot.copy()
    for field in fields:
        frame['quarter_'+field] = np.nan
    for i, row in frame.iterrows():
        if row.period_semantics == 'QUARTER_ONLY':
            for field in fields:
                frame.loc[i, 'quarter_'+field] = row.get(field, np.nan)
            continue
        if row.period_semantics not in ('YTD', 'ANNUAL'):
            continue
        previous_end = pd.Timestamp(row.period_end) - pd.DateOffset(months=3)
        previous = frame[(frame.instrument_id == row.instrument_id) & (frame.basis == row.basis)
                         & (frame.period_start == row.period_start)
                         & (pd.to_datetime(frame.period_end).sub(previous_end).abs() <= pd.Timedelta(days=3))]
        if len(previous) != 1:
            continue
        for field in fields:
            a, b = row.get(field), previous.iloc[0].get(field)
            if pd.notna(a) and pd.notna(b):
                frame.loc[i, 'quarter_'+field] = a-b
    return frame


def pit_shares_outstanding(anchors, events, instrument_id, signal_timestamp, *, evidence_complete=False):
    """Reconstruct raw shares from dated anchors and verified capital changes.

    Callers must independently certify event coverage. A current anchor cannot
    travel backward. Unknown mergers/issuance/buyback terms invalidate value.
    """
    cutoff = pd.Timestamp(signal_timestamp)
    if cutoff.tzinfo is None:
        raise ValueError('signal_timestamp requires an explicit timezone')
    invalid = dict(shares_outstanding=None, value_feature_valid=False, reason='INCOMPLETE_SHARE_EVIDENCE',
                   known_at=None, effective_date=None, source=[], verification_status='NEEDS_REVIEW')
    if anchors.empty or evidence_complete is not True:
        return invalid
    day = cutoff.tz_convert('Asia/Kolkata').tz_localize(None).normalize()
    known = anchors[(anchors.instrument_id == instrument_id) & anchors.verification_status.eq('VERIFIED')
                    & evidence_known_times(anchors, 'exchange_disseminated_at').le(cutoff)
                    & pd.to_datetime(anchors.effective_date).le(day)].reset_index(drop=True)
    if known.empty:
        return invalid
    provenance = known.get('source_sha256', pd.Series('', index=known.index)).astype('string').str.fullmatch('[0-9a-f]{64}', na=False)
    if not provenance.all() or known.duplicated(['effective_date', 'exchange_disseminated_at']).any():
        return invalid
    anchor = known.sort_values(['effective_date', 'exchange_disseminated_at']).iloc[-1]
    shares = number_or_nan(anchor.shares_outstanding)
    known_at = evidence_known_times(known, 'exchange_disseminated_at').loc[anchor.name]
    effective = pd.Timestamp(anchor.effective_date)
    sources = [anchor.source_sha256]
    if not np.isfinite(shares) or shares <= 0:
        return invalid
    if not events.empty:
        announced = evidence_known_times(events, 'announced_at')
        changes = events[(events.instrument_id == instrument_id)
                         & (announced.le(cutoff) | announced.isna())
                         & pd.to_datetime(events.effective_date).gt(pd.Timestamp(anchor.effective_date))
                         & pd.to_datetime(events.effective_date).le(day)]
        if (not changes.verification_status.eq('VERIFIED').all()
                or evidence_known_times(changes, 'announced_at').isna().any()
                or not evidence_known_times(changes, 'announced_at').le(cutoff).all()
                or changes.duplicated('effective_date').any()):
            return invalid
        if not changes.get('source_sha256', pd.Series('', index=changes.index)).astype('string').str.fullmatch('[0-9a-f]{64}', na=False).all():
            return invalid
        for row in changes.sort_values('effective_date').to_dict('records'):
            known_at = max(known_at, pd.Timestamp(row['announced_at']),
                           pd.Timestamp(row['known_at']) if pd.notna(row.get('known_at')) else pd.Timestamp(row['announced_at']))
            effective = max(effective, pd.Timestamp(row['effective_date']))
            sources.append(row['source_sha256'])
            if row['event_type'] in ('SPLIT', 'BONUS') and pd.notna(row.get('share_multiplier')):
                multiplier = number_or_nan(row['share_multiplier'])
                if not np.isfinite(multiplier) or multiplier <= 0:
                    return invalid
                shares *= multiplier
            elif row['event_type'] in ('BUYBACK', 'ISSUANCE', 'MERGER') and pd.notna(row.get('shares_after')) and not any(
                    pd.notna(row.get(k)) for k in ('shares_added', 'shares_removed', 'share_multiplier')):
                # Legacy replay helper; certified batch callers independently
                # reconcile arithmetic and never certify from this value alone.
                shares = number_or_nan(row['shares_after'])
            else:
                from quant.data.capital_events import replay_capital_event
                try:
                    shares = replay_capital_event(shares, row)
                except ValueError:
                    return invalid
    if not np.isfinite(shares) or shares <= 0:
        return invalid
    return dict(shares_outstanding=shares, value_feature_valid=True, reason='VERIFIED_PIT_SHARE_EVIDENCE',
                known_at=known_at.isoformat(), effective_date=str(effective.date()),
                source=sorted(set(sources)), verification_status='VERIFIED')
