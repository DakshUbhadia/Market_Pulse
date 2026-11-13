import numpy as np
import pandas as pd


def liquidity_features(panel):
    value = panel.traded_value
    volume = panel.volume
    returns = panel.adjusted_close.pct_change(fill_method=None)
    result = pd.DataFrame(index=panel.index)
    for days in (20, 60):
        result[f'adv_{days}'] = value.rolling(days, min_periods=int(np.ceil(.95 * days))).median()
    result['relative_volume_20'] = volume / volume.rolling(20, min_periods=19).median().replace(0, np.nan)
    delivery = panel['deliverable_percent'] if 'deliverable_percent' in panel else pd.Series(np.nan, index=panel.index)
    result['delivery_pct_20'] = delivery.rolling(20, min_periods=19).mean()
    result['turnover_20'] = value.rolling(20, min_periods=19).sum()  # INR traded value; not a free-float share ratio.
    result['amihud_60'] = (returns.abs() / value.where(value > 0)).rolling(60, min_periods=57).median()
    result['trading_presence_252'] = (panel.observed & volume.gt(0)).rolling(252, min_periods=1).sum() / 252
    return result
