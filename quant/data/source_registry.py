"""Implemented source capabilities; future adapters are not advertised as ready."""
SOURCES = {
    'nse_calendar': {'required': True, 'frequency': 'DAILY', 'credential': None},
    'nse_bhavcopy': {'required': True, 'frequency': 'TRADING_DAY', 'credential': None},
    'dhan_instruments': {'required': False, 'frequency': 'DAILY', 'credential': None},
    'nse_delivery': {'required': False, 'frequency': 'TRADING_DAY', 'credential': None},
    'nse_security_master': {'required': True, 'frequency': 'DAILY', 'credential': None},
    'security_history': {'required': True, 'frequency': 'DAILY', 'credential': None},
    'adjusted_prices': {'required': True, 'frequency': 'DAILY', 'credential': None},
    'nse_corporate_actions': {'required': True, 'frequency': 'DAILY', 'credential': None},
    'nse_indices': {'required': True, 'frequency': 'TRADING_DAY', 'credential': None},
    'nse_vix': {'required': True, 'frequency': 'TRADING_DAY', 'credential': None},
    'nse_financials': {'required': False, 'frequency': 'DAILY', 'flag': 'enable_fundamentals'},
    'nse_shareholding': {'required': False, 'frequency': 'DAILY', 'flag': 'enable_shareholding'},
    'nse_announcements': {'required': False, 'frequency': 'DAILY', 'flag': 'enable_announcements'},
    'nse_flows': {'required': False, 'frequency': 'DAILY', 'flag': 'enable_fiidii'},
    'rbi': {'required': False, 'frequency': 'DAILY', 'flag': 'enable_rbi'},
    'angel': {'required': False, 'frequency': 'LIVE', 'flag': 'enable_angel', 'implemented': False},
    'derivatives': {'required': False, 'frequency': 'TRADING_DAY', 'flag': 'enable_derivatives', 'implemented': False},
}


def source_status(config, state, *, as_of):
    """A flag is intent, not evidence of ingestion or freshness."""
    result = {}
    for name, spec in SOURCES.items():
        row = dict(spec)
        observed = state.get(name, {})
        if spec.get('flag') and not getattr(config, spec['flag']):
            row['status'] = 'DISABLED'
        elif spec.get('implemented', True) is False:
            row['status'] = 'NOT_IMPLEMENTED'
        elif not observed:
            row['status'] = 'FAILED'
            row['reason'] = 'No validated observation'
        else:
            row.update(observed)
            stamp = observed.get('last_successful_at')
            if row.get('status') == 'READY' and (not stamp or stamp[:10] < str(as_of)):
                row['status'] = 'STALE'
        result[name] = row
    return result
