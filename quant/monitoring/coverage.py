"""Alert on individual cutoff coverage degradation."""
import math


def coverage_health(overall, top100, *, parser_attempts=0, parser_failures=0):
    if parser_attempts < 0 or not 0 <= parser_failures <= parser_attempts:
        raise ValueError('Invalid parser observation counts')
    valid = all(v is not None and math.isfinite(v) and 0 <= v <= 1 for v in (overall, top100))
    rate = parser_failures/parser_attempts if parser_attempts else None
    return dict(status=('ALERT' if overall < .8 or top100 < .9 or rate is not None and rate > .2
                        else 'PASS' if rate is not None else 'UNASSESSED') if valid else 'UNASSESSED',
        overall_coverage=overall, top100_coverage=top100, parser_failure_rate=rate, action='REVIEW_ONLY')
