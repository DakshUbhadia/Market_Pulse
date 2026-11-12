"""Publish adjusted partitions only after price and corporate coverage pass."""
import json

import pandas as pd

from quant.features.adjustments import adjust_prices
from quant.features.returns import calculate_returns
from quant.pipeline.audit_prices import audit_prices
from quant.pipeline.state import PipelineState
from quant.storage.duckdb_store import query_prices
from quant.data.normalization import write_daily
from quant.data.http import atomic_write


def build_adjusted(config, start, end):
    state = PipelineState(config)
    action_state = state.data.get('nse_corporate_actions', {})
    if (action_state.get('status') != 'READY' or action_state.get('checked_through', '') < str(end)
            or action_state.get('checked_from', '9999-12-31') > str(start)):
        raise ValueError('Corporate-action coverage is incomplete; adjusted research is unavailable')
    if audit_prices(config, start, end)['status'] != 'READY':
        raise ValueError('Price audit must pass before adjusted prices can be generated')
    files = list((config.data_dir / 'normalized' / 'corporate_actions').rglob('*.parquet'))
    actions = pd.concat([pd.read_parquet(path) for path in files], ignore_index=True) if files else pd.DataFrame()
    if not actions.empty:
        actions = actions.drop_duplicates('event_id')
    prices = query_prices(config.prices_dir, start=start, end=end)
    adjusted = calculate_returns(adjust_prices(prices, actions))
    paths = write_daily(adjusted, config.data_dir / 'normalized' / 'adjusted_prices')
    report = {'status': 'READY', 'rows': len(adjusted), 'partitions': len(paths),
              'excluded_symbols': sorted(adjusted.loc[adjusted.adjustment_status != 'OK', 'symbol'].unique().tolist()),
              'from': str(start), 'to': str(end)}
    state.record('adjusted_prices', day=end, **report)
    atomic_write(config.data_dir / 'reports' / f'adjustments-{end}.json', json.dumps(report, indent=2).encode())
    return report
