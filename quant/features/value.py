"""Value uses raw contemporaneous prices and verified contemporaneous shares."""
import numpy as np
from quant.features.fundamentals import ratio
from quant.features.fundamental_snapshot import number_or_nan

VALUE_FIELDS = {'earnings_yield': 1, 'fcf_yield': 1, 'book_yield': 1}


def value_features(row, *, raw_price, shares):
    result = {name: np.nan for name in VALUE_FIELDS}
    if not row.get('annual_fresh') or shares.get('value_feature_valid') is not True:
        return result
    try:
        price, count = float(raw_price), float(shares['shares_outstanding'])
    except (ValueError, TypeError, KeyError):
        return result
    if not np.isfinite(price) or not np.isfinite(count) or min(price,count) <= 0:
        return result
    market_cap = price*count
    result['earnings_yield'] = ratio(row.get('annual_pat'), market_cap)
    result['book_yield'] = ratio(row.get('annual_equity'), market_cap)
    cfo, capex = number_or_nan(row.get('annual_operating_cash_flow')), number_or_nan(row.get('annual_capex'))
    if np.isfinite([cfo,capex]).all() and capex >= 0:
        result['fcf_yield'] = ratio(cfo-capex, market_cap)
    return result
