# Quant data foundation

This package is independent of the Next.js application. It collects free source
data and transforms it for research. It does not rank stocks, run inference,
publish recommendations, or place orders.

## Setup

From the repository root in PowerShell:

```powershell
python -m venv quant/.venv
quant/.venv/Scripts/python.exe -m pip install -r quant/requirements.txt
quant/.venv/Scripts/python.exe -c "from quant.config import Config; print(Config())"
quant/.venv/Scripts/python.exe -m pytest quant/tests -m "not integration" -q
```

The root `.env` loads automatically. Process environment values take precedence.
Relative `QUANT_DATA_DIR` paths resolve from the repository root. Optional filing,
macro, flow and live-data switches default to false. Enabling a switch alone
never makes that source ready. Angel and derivatives remain `NOT_IMPLEMENTED`;
the completion guide postpones them until the EOD foundation is validated.

## Historical bootstrap and coverage gates

```powershell
quant/.venv/Scripts/python.exe -m quant.pipeline.update_calendar --from 2018-01-01 --to 2026-11-09
quant/.venv/Scripts/python.exe -m quant.pipeline.bootstrap_history --from 2018-01-01 --to 2026-11-09 --calendar cached --skip-instruments
quant/.venv/Scripts/python.exe -m quant.pipeline.audit_prices --from 2018-01-01 --to 2026-11-09
```

Replace the example end date with the latest completed EOD date. `--calendar`
accepts `auto`, `cached`, and `none`; `probe` remains a compatibility alias for
`none`. `--trading-dates` is an advanced override. A 404 is recorded as unresolved,
never converted into a holiday. A malformed cached object and its sidecar are
removed and the network is tried once more. Successful downloads retain their
bytes and SHA-256 provenance.

After the 2018 audit passes, extend history:

```powershell
quant/.venv/Scripts/python.exe -m quant.pipeline.update_calendar --from 2010-01-01 --to 2026-11-09
quant/.venv/Scripts/python.exe -m quant.pipeline.bootstrap_history --from 2010-01-01 --to 2026-11-09 --calendar cached --skip-instruments
quant/.venv/Scripts/python.exe -m quant.pipeline.audit_prices --from 2010-01-01 --to 2026-11-09
quant/.venv/Scripts/python.exe -m quant.pipeline.update_all --from 2010-01-01
```

The gate requires at least 99.5% session coverage, no duplicate keys, invalid bars,
unexpected sessions or corrupt partitions. Calendar verification is reconciled
against actual partition contents. Deleting or corrupting a partition revokes its
verified status. Every refresh rechecks expected sessions, so an old hole cannot
be hidden by a recent success watermark.

For 2010, which the holiday API does not serve, calendar refresh automatically
downloads and validates NSE circular `cmtr13713.pdf` (download number 13713).
Its title, calendar year and holiday rows must match before it can be used. Later
years use the holiday API. A missing historical source still fails visibly.
Calendar refresh also checks official NIFTY history in monthly windows, adding
positively observed special sessions such as 2010-02-06. Missing index rows never
prove a holiday. Completed historical windows reuse checksummed raw archives;
recent windows are refreshed. Monthly requests avoid the endpoint's observed
truncation of longer ranges.

## Refresh commands

`update_all` runs calendar, market EOD, corporate, macro, adjusted-price generation,
and validation in order. Separate commands are also available:

```powershell
quant/.venv/Scripts/python.exe -m quant.pipeline.update_market_eod --from 2018-01-01
quant/.venv/Scripts/python.exe -m quant.pipeline.update_corporate --from 2018-01-01
quant/.venv/Scripts/python.exe -m quant.pipeline.update_macro --from 2018-01-01
quant/.venv/Scripts/python.exe -m quant.pipeline.validate_data --from 2018-01-01
```

EOD uses the official calendar, including special weekend sessions. The default
cutoff includes today after 18:30 Asia/Kolkata. An unavailable archive is a failure;
the cutoff does not assert that NSE has published it. Corporate polling resumes
from its last successful window with a 14-day overlap to capture revisions. Initial
corporate history is fetched in bounded windows. Raw response versions are
archived before parsing. Financial XBRL and shareholding XML are separately retained.

`data/state/pipeline_state.json` records per-source progress. Reports include
`price-audit-YYYYMMDD.json`, `calendar-health.json`, source-specific run reports,
and `data-health-YYYY-MM-DD.json`. The health manifest remains `NOT_READY` until
2010-present prices and the required sources are validated. Consumers must check
`recommendation_allowed` and the per-stock exclusions before publishing anything.
This package does not change or integrate with the existing application publisher.

## Data contracts and limitations

- NSE `EQUITY_L.csv` is the research master for listed equities. A daily snapshot
  is evidence of current listing, not historical membership or proof of active
  trading. Unpublished tick sizes remain null. Dhan is stored separately under
  `normalized/vendor_mappings/dhan` and provides vendor IDs only.
- Identity UUIDs derive from ISIN. Symbol reuse creates distinct identities;
  unresolved ISINs stay unresolved. Intervals span observed evidence only. Changes
  of ISIN are not silently stitched across a split, merger or demerger.
- Delivery joins use date, symbol and series. Turnover is converted from lakhs to
  rupees. Missing delivery stays null; delivery and flows are optional sources.
- All index rows are retained. Invalid optional index OHLC is explicitly flagged
  `INVALID_OHLC`; required benchmarks and India VIX must pass validation. Filter
  flagged rows out of research. India VIX shares the archived daily index source.
- NSE T0 close is the corresponding EQ close, per question 17 of the
  [NSE T+0 FAQ](https://nsearchives.nseindia.com/web/sites/default/files/inline-files/FAQ_Trading_in_T%2B0_Security_0.pdf).
  The parser permits this documented OHLC exception only when the EQ close matches.
  T0 prices remain excluded from adjusted-return research.
- Raw closes are immutable. Splits/bonuses adjust earlier prices. Dividend total
  returns assume reinvestment at the ex-date close. Ambiguous, overlapping and
  unsupported actions exclude affected identities; rights, mergers and demergers
  require review. This is deliberate, rather than inferring missing economics.
- Financial XBRL extraction uses explicit concepts, periods and consolidation
  contexts. Ambiguous quarter/YTD, segment or unit combinations remain null.
  Banks have a separate schema; there is no EV/EBITDA computation for banks.
  Unsupported taxonomy concepts remain in the raw XML and require parser work.
- Filings become usable only after the exchange dissemination timestamp. Received
  time and first-seen time do not substitute for it. Revisions remain distinct
  versions. `available_filings` selects versions available at a supplied instant.
- The requested [RBIH DBIE API](https://dev.dbie.rbihub.in/docs/using-the-site) is a
  DBIE mirror. `rbi_series_registry.json` defines the seven requested series and
  their exact table mappings. Missing/stale values are reported. Its publication
  tables can contain missing or malformed historical cells. Release timestamps
  are not supplied reliably: those observations retain null `publication_date`
  and `timing_status=UNCERTAIN`. `available_macro` excludes them from backtests.
  Fetching today's revised history cannot reconstruct historical data vintages.
- FII/DII is a provisional current snapshot. The endpoint is not represented as
  a complete historical archive, and its values remain explicitly in INR crore.

## Research access

Parquet is authoritative; DuckDB scans it directly without another full database:

```python
from quant.config import Config
from quant.storage.duckdb_store import research_connection, query_dataset

config = Config()
prices = query_dataset(config.data_dir, 'prices', symbol='RELIANCE')
with research_connection(config.data_dir) as connection:
    sample = connection.execute('SELECT * FROM prices LIMIT 10').fetchdf()
```

Views cover prices, delivery, adjusted prices, NSE instruments, corporate actions,
indices, VIX, financials, shareholding, announcements, macro and flows when their
datasets exist. Corporate queries expose observed versions; deduplicate by stable
record/version ID and apply the relevant availability timestamp for research.

## Scheduling and live tests

Create a Windows Task Scheduler task that runs PowerShell with arguments:

```text
-NoProfile -ExecutionPolicy Bypass -File "C:\path\to\Market_Pulse\scripts\run_quant_eod.ps1" -From 2010-01-01
```

Use 18:30 IST, enable **Run task as soon as possible after a scheduled start is
missed**, and select **Do not start a new instance**. Use the 2018 start until its
audit passes and the 2010 extension is loaded. An optional second task at 21:00 IST
can append `-CorporateOnly`. The script resolves paths from its own location and
propagates the pipeline exit code. No task is registered automatically by importing
or testing the package.

Run live tests explicitly; routine PR/push CI uses synthetic unit tests:

```powershell
quant/.venv/Scripts/python.exe -m pytest quant/tests/integration -m integration -q
```

The manual GitHub Actions integration workflow tests archive formats, current
master, calendar, delivery, indices/VIX, and the real 2024 Reliance bonus. Exchange
blocking or changed source schemas fail visibly; they are not skipped as success.
