"""Implemented source capabilities; future adapters are not advertised as ready."""
SOURCES = {
    'nse_calendar': {'required': True, 'frequency': 'DAILY', 'credential': None},
    'nse_bhavcopy': {'required': True, 'frequency': 'TRADING_DAY', 'credential': None},
    'dhan_instruments': {'required': False, 'frequency': 'DAILY', 'credential': None},
}
