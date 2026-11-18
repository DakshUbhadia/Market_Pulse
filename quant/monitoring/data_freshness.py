"""Freshness follows certified exchange sessions rather than elapsed weekdays."""


def data_freshness(sources, *, required_session):
    rows = [dict(source_id=r['source_id'], last_verified_session=r.get('last_verified_session'),
        status='PASS' if r.get('current_eod_ready') == 'READY' and r.get('last_verified_session') == str(required_session)
        else 'ALERT') for r in sources if r.get('required_for_forward_refresh')]
    return dict(status='PASS' if rows and all(r['status'] == 'PASS' for r in rows) else 'ALERT',
                sources=rows, required_session=str(required_session), action='REVIEW_ONLY')
