"""Dated delivery-cost inputs and component-level source provenance.

Prior to October 2024 the member-volume slab and client/state contract are
unknown. Those eras remain proxies even when individual statutory rates are
known. Brokerage, DP, slippage and impact are declared research assumptions.
"""
from datetime import date

NSE_LEVIES = 'https://www.nseindia.com/static/invest/first-time-investor-sebi-turnover-fees-stt-other-levies'
GST_SOURCE = 'https://cbic-gst.gov.in/sectoral-faq.html'
KKC_SOURCE = 'https://ies.gov.in/arthapedia/concept/krishi-kalyan-cess-kkc'
EXCHANGE_2023 = 'https://nsearchives.nseindia.com/content/circulars/FA56129.pdf'
EXCHANGE_2024 = 'https://nsearchives.nseindia.com/content/circulars/FA64232.pdf'
EXCHANGE_2026 = 'https://nsearchives.nseindia.com/content/circulars/FA73061.pdf'
BROKER_SOURCE = 'https://zerodha.com/charges'


def historical_schedule_parameters():
    # Exclusive upper bounds. 2016 is the first supported research year;
    # no fallback applies one modern schedule to arbitrary older dates.
    eras = [
        (date(2016,1,1), date(2016,6,1), .145, .0000325, .000000001),
        (date(2016,6,1), date(2017,7,1), .15, .0000325, .000000001),
        (date(2017,7,1), date(2020,7,1), .18, .0000325, .000000001),
        (date(2020,7,1), date(2021,1,1), .18, .0000325, .000000001),
        (date(2021,1,1), date(2023,4,1), .18, .0000345, .000000001),
        (date(2023,4,1), date(2024,4,1), .18, .0000325, .000001),
        (date(2024,4,1), date(2024,10,1), .18, .0000322, .000001),
    ]
    return tuple(dict(effective_from=start, effective_to=end, brokerage_rate=.0003,
        exchange_rate=exchange, ipft_rate=ipft, sebi_rate=.000002, gst_rate=tax,
        stamp_buy=.0003 if start < date(2020,7,1) else .00015,
        stamp_sell=.0003 if start < date(2020,7,1) else 0, dp_sell=13.5, verified=False)
        for start,end,tax,exchange,ipft in eras)


def charge_table(schedule):
    """Long-format schedule contract, including side and the tax calculation base."""
    day = schedule.effective_from
    tax_name = 'service_tax' if day < date(2017,7,1) else 'gst'
    exchange_source = EXCHANGE_2026 if day >= date(2026,3,1) else (
        EXCHANGE_2024 if day >= date(2024,10,1) else EXCHANGE_2023)
    entries = [
        ('stt', schedule.stt_rate, 'TURNOVER', NSE_LEVIES, schedule.verified, 'BOTH'),
        ('exchange', schedule.exchange_rate, 'TURNOVER', exchange_source, schedule.verified, 'BOTH'),
        ('ipft', schedule.ipft_rate, 'TURNOVER', exchange_source, schedule.verified, 'BOTH'),
        ('sebi', schedule.sebi_rate, 'TURNOVER', NSE_LEVIES, schedule.verified, 'BOTH'),
        (tax_name, schedule.gst_rate, 'TAXABLE_FEES', KKC_SOURCE if tax_name == 'service_tax' else GST_SOURCE,
            day >= date(2017,7,1), 'BOTH'),
        ('stamp_duty', schedule.stamp_buy, 'TURNOVER', NSE_LEVIES, day >= date(2020,7,1), 'BUY'),
        ('stamp_duty', schedule.stamp_sell, 'TURNOVER', NSE_LEVIES, day >= date(2020,7,1), 'SELL'),
        ('brokerage', schedule.brokerage_rate, 'TURNOVER', BROKER_SOURCE + ' (research assumption)', False, 'BOTH'),
        ('dp_charge', schedule.dp_sell, 'PER_INSTRUMENT_SALE_DAY', BROKER_SOURCE + ' (research assumption)', False, 'SELL'),
    ]
    return [dict(effective_from=str(day), effective_to=str(schedule.effective_to) if schedule.effective_to else None,
        product='DELIVERY', side=side, charge_type=name, rate_type=kind, rate=rate,
        source_reference=source, verified=verified) for name,rate,kind,source,verified,side in entries]
