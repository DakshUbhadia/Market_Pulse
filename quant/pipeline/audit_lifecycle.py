"""Separate archived event integrity, PIT coverage, and observed held valuation."""
import json
from datetime import date

import numpy as np
import pandas as pd

from quant.pipeline.backfill_lifecycle import load_lifecycle
from quant.storage.research_store import write_json
from quant.data.security_history import instrument_id


def audit_lifecycle(config, *, as_of=None, holdings=None, lifecycle_records=None, scores=None,
                    portfolio_sessions=None, write=True):
    from quant.lifecycle.state import simulation_time
    from quant.lifecycle.policy import LIFECYCLE_POLICY_VERSION
    errors, frame = [], pd.DataFrame()
    try:
        frame = load_lifecycle(config)
        if not frame.empty:
            if frame.lifecycle_event_id.duplicated().any():
                raise ValueError('Duplicate lifecycle event IDs')
            frame['announced_at'] = pd.to_datetime(frame.announced_at,utc=True)
            frame = frame[frame.announced_at.le(simulation_time(as_of,'23:59:59'))] if as_of else frame
            verified = frame[frame.verification_status.eq('VERIFIED')]
            if (verified.announced_at.isna().any() or verified.effective_date.isna().any()
                    or not verified.instrument_id.eq(verified['isin'].map(instrument_id)).all()):
                raise ValueError('Invalid verified lifecycle identity or timing')
    except (OSError,ValueError,KeyError,TypeError) as error:
        errors.append(str(error))
    unresolved = None
    if holdings is not None:
        required = {'trade_date','instrument_id','value'}
        if not required.issubset(holdings):
            errors.append('Held lifecycle assessment requires dated identities and observed valuations')
        else:
            assessed = holdings[pd.to_datetime(holdings.trade_date).le(pd.Timestamp(as_of))] if as_of else holdings
            unresolved = int((assessed.instrument_id.isna() | ~np.isfinite(assessed.value) | assessed.value.le(0)).sum())
    verified_count = int(frame.verification_status.eq('VERIFIED').sum()) if not frame.empty else 0
    encountered, resolved, reviewed_top, by_year = None, None, None, []
    if not frame.empty:
        verified = frame[frame.verification_status.eq('VERIFIED')].copy()
        verified['year'] = pd.to_datetime(verified.effective_date).dt.year
        for year, group in verified.groupby('year'):
            by_year.append(dict(year=int(year), verified_events=len(group), coverage_status='UNESTABLISHED'))
        if holdings is not None and {'trade_date','instrument_id'}.issubset(holdings):
            # Economic event records are also proof of a prior holding even
            # when conversion/cash removes it before that day's close snapshot.
            encountered_ids = set()
            holding_days = pd.DatetimeIndex(pd.to_datetime(portfolio_sessions if portfolio_sessions is not None
                else holdings.trade_date).drop_duplicates()).sort_values()
            for event in verified.itertuples():
                if event.optional:
                    continue  # Optional offers are never baseline obligations.
                day = pd.Timestamp(event.effective_date)
                previous = holding_days[holding_days < day]
                if (not len(previous) or not len(holding_days) or day > holding_days[-1]
                        or event.announced_at > simulation_time(day,'23:59:59')):
                    continue
                # The complete portfolio's prior snapshot proves ownership.
                # Selecting the identity's own last row would count already-sold names.
                prior = holdings[pd.to_datetime(holdings.trade_date).eq(previous[-1])]
                if prior.instrument_id.eq(event.instrument_id).any():
                    encountered_ids.add(event.lifecycle_event_id)
            resolved_ids = set()
            if lifecycle_records is not None and not lifecycle_records.empty:
                records = lifecycle_records
                if as_of:
                    records = records[pd.to_datetime(records.trade_date).le(pd.Timestamp(as_of))]
                valid_records = records[records.event_type.isin(['CASH_SETTLEMENT','SHARE_CONVERSION','ZERO_RECOVERY'])]
                resolved_ids = set(valid_records.event_id.dropna()) & set(verified.lifecycle_event_id)
                encountered_ids |= resolved_ids
            encountered = len(encountered_ids)
            # Resolution of the economic event also resolves the related
            # suspension/delisting review only when dated mandatory economics
            # actually executed for the same held identity.
            resolved = 0
            for event in verified[verified.lifecycle_event_id.isin(encountered_ids)].itertuples():
                related = verified[verified.instrument_id.eq(event.instrument_id)
                    & verified.lifecycle_event_id.isin(resolved_ids)
                    & pd.to_datetime(verified.effective_date).ge(pd.Timestamp(event.effective_date))]
                resolved += int(not related.empty)
        if scores is not None and not scores.empty:
            top = scores[scores.percentile_score.ge(90)]
            if as_of:
                top = top[pd.to_datetime(top.as_of).le(pd.Timestamp(as_of))]
            reviewed_top = int(verified.instrument_id.isin(top.instrument_id).sum())
    if holdings is not None and frame.empty:
        encountered, resolved = 0, 0
    if scores is not None and frame.empty:
        reviewed_top = 0
    held_unresolved = max(encountered-resolved, unresolved or 0) if encountered is not None else unresolved
    complete_held_assessment = lifecycle_records is not None and holdings is not None and portfolio_sessions is not None
    result = dict(status='BLOCKED' if errors or unresolved or (complete_held_assessment and held_unresolved)
        else ('EVIDENCE_ONLY' if verified_count else 'NOT_READY'),
        as_of=str(as_of) if as_of else None, lifecycle_policy_version=LIFECYCLE_POLICY_VERSION,
        lifecycle_data_ready=False, lifecycle_coverage_start=None, coverage_status='UNESTABLISHED',
        verified_events=verified_count, events=len(frame),
        held_events_encountered=encountered, held_events_resolved=resolved,
        held_events_unresolved=held_unresolved,
        held_event_assessment=('ASSESSED' if portfolio_sessions is not None else 'PARTIAL')
            if lifecycle_records is not None and holdings is not None else 'UNASSESSED',
        top_decile_events_reviewed=reviewed_top, coverage_by_year=by_year,
        unresolved_held_lifecycle_events=unresolved,
        held_valuation_assessment='ASSESSED' if unresolved is not None else 'UNASSESSED',
        errors=errors, reason='Archived events do not establish complete historical universe coverage')
    if write:
        write_json(config.data_dir/'reports/lifecycle-audit.json',result)
    return result


def main():
    from quant.pipeline.cli import parser_config
    parser,config = parser_config(__doc__)
    parser.add_argument('--as-of',type=date.fromisoformat)
    args = parser.parse_args()
    result = audit_lifecycle(args.config(config),as_of=args.as_of or args.end)
    print(json.dumps(result,indent=2))
    return 0 if result['status'] == 'READY' else 1


if __name__ == '__main__':
    raise SystemExit(main())
