"""PIT lineage labels do not change instrument keys or feature history."""


def lineage_id(instrument_id, transitions, cutoff):
    known = transitions[transitions.verification_status.eq('VERIFIED_COMPLETE')
        & transitions.announced_at.le(cutoff)]
    rows = known[known.predecessor_instrument_id.eq(instrument_id) | known.successor_instrument_id.eq(instrument_id)]
    return rows.security_lineage_id.iloc[0] if len(rows) else instrument_id
