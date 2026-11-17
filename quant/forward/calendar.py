"""Use dated exchange schedules for the next open, including holiday boundaries."""
from datetime import timedelta

import pandas as pd

from quant.data.nse_calendar import (HOLIDAY_PATH, HOLIDAY_PAGE, parse_holidays,
                                    parse_muhurat_notice, build_calendar)
from quant.data.nse_client import NseClient
from quant.lifecycle.state import simulation_time
from quant.pipeline.update_calendar import read_calendar


def next_session_open(config, as_of):
    end = as_of+timedelta(days=14)
    try:
        frame = read_calendar(config,as_of+timedelta(days=1),end)
    except ValueError:
        # Historical calendars normally stop at the last observed EOD. A future
        # schedule is derived separately; it never certifies future price data.
        with NseClient(config) as client:
            events, sources = {}, {}
            for year in range(as_of.year,end.year+1):
                payload = client.get_json(HOLIDAY_PATH,params={'type':'trading','year':year},
                    referer=config.nse_base_url+HOLIDAY_PAGE,dataset='calendar')
                sources[year] = client.last_response
                events[year] = parse_holidays(payload,year,client.last_response)
            content = client.get_bytes(HOLIDAY_PAGE,dataset='calendar',suffix='html')
            specials = parse_muhurat_notice(content,client.last_response)
            frame = build_calendar(as_of+timedelta(days=1),end,events,sources,
                special_events=specials,normalized_at=pd.Timestamp.now(tz='UTC').isoformat())
    if frame.needs_investigation.any():
        raise ValueError('Next exchange schedule contains unresolved session dates')
    following = frame[frame.is_trading_session].sort_values('trade_date')
    if following.empty:
        raise ValueError('Next exchange session is not established')
    session = following.iloc[0]
    if session.session_type != 'NORMAL':
        raise ValueError('Special-session opening time requires explicit execution support')
    evidence = dict(session_date=str(session.trade_date.date()),session_type=session.session_type,
        calendar_source_url=session.get('calendar_source_url',session.get('source_url')),
        calendar_raw_sha256=session.get('calendar_raw_sha256',session.get('raw_sha256')))
    return simulation_time(session.trade_date,'09:15'), evidence
