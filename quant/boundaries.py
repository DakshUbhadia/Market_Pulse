"""Historical boundaries. Identity coverage is proved from observations, never a master backfill."""
from datetime import date

import pandas as pd

RAW_PRICE_START = date(2010, 1, 1)
DEFAULT_BACKTEST_START = date(2016, 1, 1)
MIN_HISTORY_SESSIONS = 252


def identity_boundary(sessions, resolved_sessions, requested_start, min_history_sessions=MIN_HISTORY_SESSIONS):
    """Require an uninterrupted resolved suffix and a full session warmup.

    A later gap fails the boundary; it must not silently move the start forward.
    252 sessions means 252 returns, so the first signal is at offset 252.
    """
    if min_history_sessions < 1:
        raise ValueError('Minimum history must be positive')
    dates = sorted(set(sessions))
    resolved = set(resolved_sessions)
    verified = next((day for day in dates if day in resolved), None)
    gaps = [day for day in dates if verified is not None and day >= verified and day not in resolved]
    offset = dates.index(verified) + min_history_sessions if verified else len(dates)
    signal = dates[offset] if offset < len(dates) else None
    return dict(verified_identity_start=str(verified) if verified else None,
                first_possible_signal_date=str(signal) if signal else None,
                requested_backtest_start=str(requested_start), min_history_sessions=min_history_sessions,
                identity_gaps_after_boundary=[str(day) for day in gaps],
                identity_ready_for_requested_window=bool(signal and not gaps and
                    pd.Timestamp(requested_start) >= pd.Timestamp(signal)))
