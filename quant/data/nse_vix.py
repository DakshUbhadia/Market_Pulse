"""India VIX is extracted from the official daily index report."""
from quant.data.normalization import keys


def from_indices(indices):
    frame = indices.loc[indices.index_name.str.upper().isin(['INDIA VIX', 'NIFTY INDIA VIX'])].copy()
    keys(frame, ['trade_date'])
    if frame[['open', 'high', 'low', 'close']].isna().any().any():
        raise ValueError('India VIX OHLC missing')
    if 'data_quality' in frame and frame.data_quality.ne('OK').any():
        raise ValueError('Invalid India VIX OHLC')
    return frame.drop(columns=['index_name', 'shares_traded', 'turnover'])
