from datetime import date
from pathlib import Path

import pandas as pd
import pytest

from quant.data.nse_delivery import parse_delivery
from quant.data.nse_security_master import parse_security_master
from quant.data.nse_indices import parse_indices
from quant.data.nse_vix import from_indices
from quant.data.security_history import build_security_history, instrument_id, resolve_identity
from quant.data.nse_client import RawResponse
from quant.data.nse_flows import parse_flows


def raw():
    return RawResponse('https://www.nseindia.com/api/test', '2026-11-09T20:00:00+05:30',
                       'a' * 64, Path('raw.json'), 200)


def delivery(**overrides):
    row = dict(DATE1='08-Jul-2024', SYMBOL='TEST', SERIES='EQ', TTL_TRD_QNTY='100',
               TURNOVER_LACS='2', NO_OF_TRADES='10', DELIV_QTY='40', DELIV_PER='40')
    row.update(overrides)
    return pd.DataFrame([row]).to_csv(index=False).encode()


def test_delivery_values_and_nulls():
    result = parse_delivery(delivery(), date(2024, 7, 8))
    assert result.traded_value.iloc[0] == 200_000
    assert result.deliverable_quantity.iloc[0] == 40
    result = parse_delivery(delivery(DELIV_QTY='-', DELIV_PER='-'), date(2024, 7, 8))
    assert pd.isna(result.deliverable_quantity.iloc[0])
    assert pd.isna(result.deliverable_percent.iloc[0])


@pytest.mark.parametrize('overrides', [{'DELIV_PER': '101'}, {'TTL_TRD_QNTY': '1.5'},
                                     {'DELIV_QTY': '200'}, {'TURNOVER_LACS': 'inf'},
                                     {'DATE1': '09-Jul-2024'}, {'SYMBOL': ''}])
def test_invalid_delivery(overrides):
    with pytest.raises(ValueError):
        parse_delivery(delivery(**overrides), date(2024, 7, 8))


def test_delivery_duplicate_rejection():
    csv = delivery().decode()
    with pytest.raises(ValueError, match='Duplicate'):
        parse_delivery((csv + csv.splitlines()[1] + '\n').encode(), date(2024, 7, 8))


def test_security_master_is_nse_not_vendor():
    content = b'SYMBOL,NAME OF COMPANY,SERIES,DATE OF LISTING,ISIN NUMBER,FACE VALUE\nTEST,Company,EQ,01-Jan-2020,INE000000001,10\n'
    result = parse_security_master(content, date(2024, 7, 8))
    assert result.source.iloc[0] == 'NSE'
    assert pd.isna(result.tick_size.iloc[0])


def test_identity_rename_symbol_reuse_and_unresolved():
    frame = pd.DataFrame([
        ('2024-01-01', 'OLD', 'EQ', 'INE000000001'),
        ('2024-01-02', 'NEW', 'EQ', 'INE000000001'),
        ('2024-01-03', 'OLD', 'EQ', 'INE000000002'),
        ('2024-01-04', 'UNKNOWN', 'EQ', None),
    ], columns=['trade_date', 'symbol', 'series', 'isin'])
    history = build_security_history(frame)
    assert resolve_identity(history, 'OLD', '2024-01-01') == resolve_identity(history, 'NEW', '2024-01-02')
    assert resolve_identity(history, 'OLD', '2024-01-03') != resolve_identity(history, 'OLD', '2024-01-01')
    assert resolve_identity(history, 'UNKNOWN', '2024-01-04') is None
    assert resolve_identity(history, 'NEW', '2010-01-01') is None


def test_indices_keep_all_rows_and_extract_vix():
    content = ('Index Name,Index Date,Open Index Value,High Index Value,Low Index Value,Closing Index Value,Volume,Turnover (Rs. Cr.)\n'
               'NIFTY 50,08-07-2024,100,110,90,105,100,2\n'
               'INDIA VIX,08-07-2024,10,12,9,11,-,-\n').encode()
    result = parse_indices(content, date(2024, 7, 8))
    assert len(result) == 2
    assert result.turnover.iloc[0] == 20_000_000
    assert from_indices(result).close.iloc[0] == 11


def test_provisional_flow_reconciliation():
    record = dict(date='09-Nov-2026', category='FII/FPI', buyValue='100', sellValue='130', netValue='-30')
    result = parse_flows([record], raw())
    assert result.status.iloc[0] == 'PROVISIONAL'
    assert result.participant_type.iloc[0] == 'FII'
    with pytest.raises(ValueError, match='reconcile'):
        parse_flows([dict(record, netValue='20')], raw())


def test_optional_index_anomaly_retained_but_required_benchmark_rejected():
    header = 'Index Name,Index Date,Open Index Value,High Index Value,Low Index Value,Closing Index Value,Volume,Turnover (Rs. Cr.)\n'
    body = 'Nifty50 USD,06-11-2026,8999.85,9234.6,8919.5,9234.97,-,-\n'
    frame = parse_indices((header + body).encode(), date(2026, 11, 6))
    assert frame.data_quality.iloc[0] == 'INVALID_OHLC'
    with pytest.raises(ValueError, match='required index'):
        parse_indices((header + body.replace('Nifty50 USD', 'NIFTY 50')).encode(), date(2026, 11, 6))
