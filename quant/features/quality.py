"""Industrial quality ratios; no banking leverage proxies."""
import numpy as np
from quant.features.fundamentals import ratio

QUALITY_FIELDS = {'roe': 1, 'cfo_pat': 1, 'debt_equity': -1}


def quality_features(row):
    if row.get('entity_type') != 'IND_AS_INDUSTRIAL' or not row.get('annual_fresh'):
        return {name: np.nan for name in QUALITY_FIELDS}
    return dict(roe=ratio(row.get('annual_pat'), row.get('average_equity')),
                cfo_pat=ratio(row.get('annual_operating_cash_flow'), row.get('annual_pat')),
                debt_equity=ratio(row.get('annual_borrowings'), row.get('annual_equity')))
