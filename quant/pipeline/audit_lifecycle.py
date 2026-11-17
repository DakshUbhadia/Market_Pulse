"""Separate archived event integrity, PIT coverage, and observed held valuation."""
import json
from datetime import date

import numpy as np
import pandas as pd

from quant.pipeline.backfill_lifecycle import load_lifecycle
from quant.storage.research_store import write_json
from quant.data.security_history import instrument_id


def audit_lifecycle(config, *, as_of=None, holdings=None, write=True):
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
    result = dict(status='BLOCKED' if errors or unresolved else ('EVIDENCE_ONLY' if verified_count else 'NOT_READY'),
        as_of=str(as_of) if as_of else None, lifecycle_policy_version=LIFECYCLE_POLICY_VERSION,
        lifecycle_data_ready=False, lifecycle_coverage_start=None, coverage_status='UNESTABLISHED',
        verified_events=verified_count, events=len(frame),
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
