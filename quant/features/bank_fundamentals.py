"""Bank quality and balance growth; industrial debt ratios are excluded."""
import numpy as np
from quant.features.fundamentals import ratio

BANK_QUALITY_FIELDS = {'bank_roa': 1, 'bank_roe': 1, 'bank_gnpa': -1, 'bank_nnpa': -1}
BANK_GROWTH_FIELDS = {'deposit_yoy': 1, 'advance_yoy': 1}
BANK_VALUE_FIELDS = {'earnings_yield': 1, 'book_yield': 1}


def bank_features(row):
    result = {name: np.nan for name in (*BANK_QUALITY_FIELDS, *BANK_GROWTH_FIELDS)}
    if row.get('entity_type') != 'IND_AS_BANK':
        return result
    if row.get('annual_fresh'):
        result.update(bank_roa=ratio(row.get('annual_pat'), row.get('average_assets')),
                      bank_roe=ratio(row.get('annual_pat'), row.get('average_equity')),
                      bank_gnpa=ratio(row.get('quarter_GNPA'),row.get('quarter_advances')),
                      bank_nnpa=ratio(row.get('quarter_NNPA'),row.get('quarter_advances')))
    if row.get('quarter_fresh'):
        result.update(deposit_yoy=ratio(row.get('quarter_deposits'), row.get('prior_quarter_deposits'))-1,
                      advance_yoy=ratio(row.get('quarter_advances'), row.get('prior_quarter_advances'))-1)
    return result
