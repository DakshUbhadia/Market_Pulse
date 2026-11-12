"""Returns require resolved identity and validated adjusted prices."""
def calculate_returns(adjusted):
    frame = adjusted.sort_values(['instrument_id', 'series', 'trade_date']).copy()
    if frame.loc[frame.instrument_id.notna()].duplicated(['instrument_id', 'series', 'trade_date']).any():
        raise ValueError('Duplicate instrument/session bars')
    for column, output in [('raw_close', 'raw_return'), ('adjusted_close', 'adjusted_return'),
                           ('total_return_close', 'total_return')]:
        frame[output] = frame.groupby(['instrument_id', 'series'], dropna=False)[column].pct_change(fill_method=None)
    frame.loc[frame.adjustment_status != 'OK', ['raw_return', 'adjusted_return', 'total_return']] = float('nan')
    return frame
