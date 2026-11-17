from datetime import date

import pandas as pd

from quant.boundaries import identity_boundary


def test_boundary_preserves_raw_prefix_and_requires_session_warmup():
    sessions = list(pd.bdate_range('2011-06-01', periods=300).date)
    result = identity_boundary(sessions, sessions[15:], date(2016, 1, 1))
    assert result['verified_identity_start'] == str(sessions[15])
    assert result['first_possible_signal_date'] == str(sessions[267])
    assert result['identity_ready_for_requested_window']
    assert not identity_boundary(sessions, sessions[15:], sessions[266])['identity_ready_for_requested_window']


def test_later_identity_gap_cannot_be_hidden_by_moving_boundary():
    sessions = list(pd.bdate_range('2011-06-01', periods=300).date)
    result = identity_boundary(sessions, sessions[15:200] + sessions[201:], date(2016, 1, 1))
    assert not result['identity_ready_for_requested_window']
    assert result['verified_identity_start'] == str(sessions[15])
    assert result['identity_gaps_after_boundary'] == [str(sessions[200])]


def test_no_evidence_and_short_history_fail_closed():
    dates = list(pd.bdate_range('2024-01-01', periods=10).date)
    assert not identity_boundary(dates, [], dates[-1])['identity_ready_for_requested_window']
    assert identity_boundary(dates, dates, dates[-1])['first_possible_signal_date'] is None
