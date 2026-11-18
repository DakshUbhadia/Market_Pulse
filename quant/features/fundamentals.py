"""PIT annual fundamentals and comparable quarter growth for offline research."""
import numpy as np
import pandas as pd

from quant.features.fundamental_snapshot import fundamental_snapshot, quarter_only_values, number_or_nan

from quant.version import FUNDAMENTAL_FEATURE_VERSION


def ratio(numerator, denominator, *, positive_denominator=True):
    try:
        a, b = float(numerator), float(denominator)
    except (ValueError, TypeError):
        return np.nan
    return a/b if np.isfinite(a) and np.isfinite(b) and (b > 0 if positive_denominator else b != 0) else np.nan


def fundamental_observations(filings, cutoff, *, basis='CONSOLIDATED'):
    # Keep older *then-known* statements for annual averages and YoY comparators.
    snapshot = fundamental_snapshot(filings, cutoff, basis=basis, max_age_days=1500, max_quarter_age_days=1500)
    if snapshot.empty:
        return pd.DataFrame()
    flows = ['revenue','pat','operating_cash_flow','capex','ebit','ebitda','finance_cost']
    quarters = quarter_only_values(snapshot, flows)
    day = pd.Timestamp(cutoff).tz_convert('Asia/Kolkata').tz_localize(None).normalize()
    output = []
    for identity, group in snapshot.groupby('instrument_id'):
        annuals = group[group.period_semantics.eq('ANNUAL')].sort_values('period_end')
        annual = annuals.iloc[-1].to_dict() if len(annuals) else {}
        quarter = quarters[quarters.instrument_id.eq(identity)].sort_values('period_end')
        latest = quarter.iloc[-1].to_dict() if len(quarter) else {}
        # Differencing may yield two facts for one end date. Never select one arbitrarily.
        ambiguous = len(quarter) and quarter.period_end.eq(latest['period_end']).sum() != 1
        prior = quarter[pd.to_datetime(quarter.period_end).sub(pd.Timestamp(latest['period_end'])-pd.DateOffset(years=1)).abs().le(pd.Timedelta(days=3))] if latest else quarter
        previous_annual = annuals[pd.to_datetime(annuals.period_end).sub(pd.Timestamp(annual['period_end'])-pd.DateOffset(years=1)).abs().le(pd.Timedelta(days=3))] if annual else annuals
        row = dict(instrument_id=identity, as_of=day, fundamental_feature_version=FUNDAMENTAL_FEATURE_VERSION,
                   annual_fresh=bool(annual and 0 <= (day-pd.Timestamp(annual['period_end'])).days <= 550),
                   quarter_fresh=bool(latest and not ambiguous and 0 <= (day-pd.Timestamp(latest['period_end'])).days <= 180),
                   entity_type=latest.get('entity_type', annual.get('entity_type', 'UNKNOWN')),
                   filing_ids=sorted(set(group.filing_id)), source_document_hashes=sorted(set(group.document_sha256)))
        for name in flows+['assets','equity','borrowings','cash','deposits','advances','GNPA','NNPA','nim','ROA','ROE']:
            row['annual_'+name] = annual.get(name, np.nan)
            row['quarter_'+name] = latest.get('quarter_'+name, latest.get(name, np.nan)) if not ambiguous else np.nan
            row['prior_quarter_'+name] = prior.iloc[0].get('quarter_'+name, prior.iloc[0].get(name, np.nan)) if len(prior)==1 else np.nan
        for name in ('assets','equity'):
            row['average_'+name] = (number_or_nan(annual.get(name))+number_or_nan(previous_annual.iloc[0].get(name)))/2 if len(previous_annual)==1 else np.nan
        output.append(row)
    return pd.DataFrame(output)
