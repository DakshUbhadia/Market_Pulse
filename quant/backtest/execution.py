import numpy as np


def executable(row):
    return (row is not None and row.get('adjustment_status') == 'OK' and row.get('series') == 'EQ'
            and np.isfinite(row.get('adjusted_open', np.nan)) and row['adjusted_open'] > 0
            and row.get('volume', 0) > 0)


def affordable_quantity(cash, price, desired, cost_model, day):
    low, high = 0.0, max(0.0, desired)
    for _ in range(50):
        quantity = (low + high)/2
        fee = cost_model.cost(date=day, side='BUY', turnover=quantity*price)['total']
        if quantity*price + fee <= cash:
            low = quantity
        else:
            high = quantity
    return low
