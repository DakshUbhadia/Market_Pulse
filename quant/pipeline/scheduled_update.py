"""Bounded daily overlap; historical integrity verification is a separate job."""
import json
from datetime import date

import pandas as pd

from quant.config import Config
from quant.pipeline.cli import completed_day
from quant.pipeline.state import PipelineState
from quant.pipeline.update_calendar import refresh_calendar
from quant.pipeline.update_all import update_all


def calculate_update_window(calendar, state, *, target=None, overlap=5):
    frame = calendar[calendar.is_trading_session].sort_values('trade_date')
    sessions = sorted(pd.to_datetime(frame.trade_date).dt.date.unique())
    if target is not None:
        sessions = [day for day in sessions if day <= target]
    if not sessions:
        raise ValueError('No completed exchange sessions in calendar')
    row = state.get('market_eod', {})
    last = row.get('last_successful_session') or row.get('last_success')
    if last is None:
        return date(2018, 1, 1), sessions[-1]
    last = date.fromisoformat(last)
    position = max((i for i, day in enumerate(sessions) if day <= last), default=0)
    return sessions[max(0, position - overlap)], sessions[-1]


def scheduled_update(config, *, target=None):
    target = target or completed_day(config)
    state = PipelineState(config)
    if config.calendar_path.exists():
        calendar = pd.read_parquet(config.calendar_path)
        # Refresh only the recent calendar tail, preserving previously verified years.
        refresh_start = min(target, calendar.trade_date.max().date()) - pd.Timedelta(days=40)
        calendar, _ = refresh_calendar(config, pd.Timestamp(refresh_start).date(), target, incremental=True)
    else:
        calendar, _ = refresh_calendar(config, date(2018, 1, 1), target)
    start, end = calculate_update_window(calendar, state.data, target=target)
    result = update_all(config, start, end, incremental=bool(state.data.get('market_eod')))
    result['update_window'] = {'from': str(start), 'to': str(end)}
    return result


def main():
    from quant.pipeline.cli import parser_config
    parser, config = parser_config(__doc__)
    args = parser.parse_args()
    result = scheduled_update(args.config(config), target=args.end)
    print(json.dumps({key: result[key] for key in ('status', 'update_window', 'errors')}, indent=2))
    return 0 if result['status'] == 'READY' else 1


if __name__ == '__main__':
    raise SystemExit(main())
