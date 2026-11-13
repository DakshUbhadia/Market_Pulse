"""Measure historical EQ identity evidence without borrowing today's master."""
import json
from datetime import date, datetime
from zoneinfo import ZoneInfo

import duckdb
import pandas as pd

from quant.pipeline.update_calendar import read_calendar
from quant.storage.research_store import write_json

MASTER_DOCUMENTATION = 'https://nsearchives.nseindia.com/content/press/Data_details_CM.pdf'


def audit_identities(config, start=date(2010, 1, 1), end=None):
    from quant.pipeline.cli import completed_day
    end = end or completed_day(config)
    calendar = read_calendar(config, start, end)
    expected = set(calendar.loc[calendar.is_trading_session, 'trade_date'].dt.date)
    files = [str(path) for path in config.prices_dir.rglob('*.parquet') if str(start) <= path.stem <= str(end)]
    if not files:
        raise ValueError('No historical price partitions to audit')
    with duckdb.connect(':memory:') as connection:
        coverage = connection.execute(
            "SELECT trade_date, count(*) AS EQ_rows, count(*) FILTER (WHERE "
            "regexp_full_match(trim(coalesce(isin,'')), 'IN[A-Z0-9]{10}')) AS resolved_rows, "
            "min(source_file) AS source_url, min(source_hash) AS source_sha256 "
            "FROM read_parquet(?, hive_partitioning=false, union_by_name=true) "
            "WHERE series='EQ' AND trade_date >= ? AND trade_date <= ? GROUP BY trade_date ORDER BY trade_date",
            [files, start, end]).fetchdf()
    coverage['year'] = pd.to_datetime(coverage.trade_date).dt.year
    years = []
    for year, rows in coverage.groupby('year'):
        total, resolved = int(rows.EQ_rows.sum()), int(rows.resolved_rows.sum())
        years.append(dict(year=int(year), sessions=len(rows), EQ_rows=total, resolved_rows=resolved,
                          unresolved_rows=total-resolved, row_coverage=resolved/total if total else 0,
                          sessions_without_resolved_EQ=int(rows.resolved_rows.eq(0).sum())))
    missing = coverage[coverage.resolved_rows.eq(0)]
    observed = set(pd.to_datetime(coverage.trade_date).dt.date)
    available = coverage[coverage.resolved_rows.gt(0)]
    now = datetime.now(ZoneInfo(config.timezone))
    report = dict(status='READY' if missing.empty and not (expected-observed) else 'NOT_READY',
        generated_at=now.isoformat(), date_range={'from':str(start),'to':str(end)},
        expected_sessions=len(expected), sessions_without_resolved_EQ=len(missing),
        first_resolved_session=str(available.trade_date.iloc[0].date()) if not available.empty else None,
        missing_price_sessions=sorted(str(day) for day in expected-observed), by_year=years,
        missing_identity_sessions=missing.drop(columns='year').to_dict('records'),
        identity_rule='Observed historical ISIN only; no backward fill from future or current master',
        required_evidence='Dated symbol/series/ISIN master or other authoritative effective-date identity evidence',
        official_master_documentation=MASTER_DOCUMENTATION, recommendations_allowed=False)
    write_json(config.data_dir/'reports'/f'identity-coverage-{now:%Y%m%d}.json', report)
    return report


def main():
    from quant.pipeline.cli import parser_config
    parser, config = parser_config(__doc__)
    parser.set_defaults(start=date(2010, 1, 1))
    args = parser.parse_args()
    try:
        report = audit_identities(args.config(config), args.start, args.end)
    except (ValueError, OSError, duckdb.Error) as error:
        print(f'Identity audit failed: {error}')
        return 1
    print(json.dumps({key:value for key,value in report.items() if key != 'missing_identity_sessions'}, indent=2))
    return 0 if report['status']=='READY' else 1


if __name__=='__main__':
    raise SystemExit(main())
