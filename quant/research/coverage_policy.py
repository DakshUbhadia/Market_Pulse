"""Coverage continuity is a per-cutoff gate, never a full-period average."""
import pandas as pd


def reliable_interval(rows, *, minimum_months=12, date_key='as_of'):
    if not isinstance(minimum_months, int) or minimum_months < 12:
        raise ValueError('Certification requires at least 12 consecutive monthly cutoffs')
    for index, row in enumerate(rows):
        suffix = rows[index:]
        periods = pd.PeriodIndex([r[date_key] for r in suffix], freq='M')
        if (len(periods) >= minimum_months and not periods.has_duplicates
                and all(b.ordinal-a.ordinal == 1 for a, b in zip(periods, periods[1:]))
                and all(r['thresholds_met'] is True for r in suffix)):
            return row[date_key]
    return None
