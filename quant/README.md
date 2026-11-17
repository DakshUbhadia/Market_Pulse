# Quant data foundation and Factor V1 research

This package is independent of the Next.js application. It collects free source
data, constructs historical eligible universes, ranks stocks with a fixed Factor
V1 model, and runs local research simulations. It does not publish recommendations
or place orders. A working research engine does not establish investment value.

## Setup

From the repository root in PowerShell:

```powershell
python -m venv quant/.venv
quant/.venv/Scripts/python.exe -m pip install -r quant/requirements.txt
quant/.venv/Scripts/python.exe -c "from quant.config import Config; print(Config())"
quant/.venv/Scripts/python.exe -m pytest quant -m "not integration" -q
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

`update_all` runs calendar, market EOD, corporate actions, adjusted OHLC,
financial/shareholding/announcement filings, macro, and validation in that order.
Fundamental ingestion can therefore verify adjusted-price readiness on its first
enabled run. Separate commands are also available:

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
Public recommendation permission remains false throughout this research phase.
This package does not integrate with the existing application publisher.

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
- Raw OHLC is immutable. Splits/bonuses adjust earlier executable OHLC. Dividends
  affect `total_return_close` only; executable OHLC is never dividend adjusted.
  Each row retains source-price SHA-256 and corporate-action input version.
  Dividend total
  returns assume reinvestment at the ex-date close. Ambiguous, overlapping and
  unsupported actions exclude affected identities from their ex-date onward;
  rights, mergers and demergers require review. Earlier dates are not excluded
  because of an unresolved future event. Historical split scaling cancels in
  ratios, returns and inverse-volatility weights; minimum-price eligibility uses
  raw close so future splits cannot change past membership.
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
-NoProfile -ExecutionPolicy Bypass -File "C:\path\to\Market_Pulse\scripts\run_quant_eod.ps1"
```

Use 18:30 IST, enable **Run task as soon as possible after a scheduled start is
missed**, and select **Do not start a new instance**. The default daily runner
uses five sessions before `market_eod.last_successful_session` through the latest
completed exchange session, repairing the overlap from refreshed raw responses.
An initial run starts in 2018. Bootstrap and audit the 2010 extension separately.
An optional second task at 21:00 IST
can append `-CorporateOnly`. The script resolves paths from its own location and
propagates the pipeline exit code. No task is registered automatically by importing
or testing the package.

Run live tests explicitly; routine PR/push CI uses synthetic unit tests:

```powershell
quant/.venv/Scripts/python.exe -m pytest quant -m integration -q
```

The manual GitHub Actions integration workflow tests archive formats, current
master, calendar, delivery, indices/VIX, and the real 2024 Reliance bonus. Exchange
blocking or changed source schemas fail visibly; they are not skipped as success.

## Research workflow

Use a completed session in place of the example dates. The readiness command
independently checks 2010 onward price coverage (at least 99.5%), duplicate keys,
OHLC, adjusted-price provenance, action-input version, identity intervals, and
Nifty 50/Nifty 500 history. Missing latest data or corrupt partitions fail closed.
Fundamentals, delivery, flows and macro are not V1 prerequisites.

```powershell
quant/.venv/Scripts/python.exe -m quant.pipeline.backfill_benchmarks --from 2010-01-01 --to 2026-11-09
quant/.venv/Scripts/python.exe -m quant.pipeline.weekly_audit --to 2026-11-09 --rebuild-adjusted
quant/.venv/Scripts/python.exe -m quant.pipeline.check_research_ready --as-of 2026-11-09 --backtest-start 2016-01-01
quant/.venv/Scripts/python.exe -m quant.pipeline.audit_fundamentals
quant/.venv/Scripts/python.exe -m quant.pipeline.audit_identities --to 2026-11-12
quant/.venv/Scripts/python.exe -m quant.pipeline.build_features --as-of 2026-11-09
quant/.venv/Scripts/python.exe -m quant.pipeline.run_factor_v1 --as-of 2026-11-09
```

Inspect `data/artifacts/factor_v1/2026-11-09-top30-review.txt` before interpreting
backtests. A score of 92 denotes a percentile rank, never a 92% profit probability.
The dated ranking Parquet/CSV and metadata are research artifacts, not orders.

Run a weekly integrity task separately using `run_quant_eod.ps1 -FullAudit`.
Delta updates fingerprint action inputs by identity and rebase the historical
bars of changed identities. Other names use the five-session overlap plus one
preceding session for return continuity. Missing baseline or identity evidence
blocks the update and requires `weekly_audit --rebuild-adjusted`; a delta must not
splice incompatible adjustment anchors. Full rebuilding uses identity buckets
and bounded month reads on disk, preserving raw inputs and limiting memory.
Daily validation uses a successful weekly audit no older than seven days; it
does not repeat a full 2010 audit. A failed rebase revokes adjustment readiness.

The universe uses each day's observed EQ bars and ISIN identities, rather than
today's constituents. EQ-series fund units are excluded using that date's observed
INF ISIN, because EQ alone does not identify a company share. No current ETF list
is backfilled into historical membership. Feature version 1.0.1 records this
universe correction; Factor V1 weights remain unchanged. It requires 252 elapsed exchange sessions, 95% trading
presence, median 60-session traded value of INR 50 million, and resolved actions.
Missing sessions stay missing, historical delisted rows remain in the data, and
old bars are never carried forward into current membership. ISIN changes require
evidence before stitching; this is survivorship-aware research with explicit
identity and delisting limitations, not a complete historical corporate lineage.

Features include prescribed momentum and Nifty 500 relative strength, realized
risk, empirical 5% tail loss, median traded value, Amihud illiquidity, and trading
presence. Missing delivery stays null. `turnover_20` is 20-session traded value in
INR, not a free-float turnover ratio; historical point-in-time shares are absent.
Per-date eligible, complete inputs are winsorized at 1%/99%, normalized using
median/MAD, and clipped to +/-3. Degenerate MAD produces zero. No label enters a
feature or normalization operation. The fixed score uses 40% momentum, 20%
relative strength, 20% low risk and 20% liquidity, with the guide's inner weights.

Labels enter at the next session's split-adjusted open and exit at t+63 close,
subtracting the same Nifty 500 holding-period price return. The final 63 sessions
are censored; missing mature exits are reported separately and do not count as
successful coverage. Cross-sectional IC uses Spearman ranks; confidence intervals
use reproducible moving blocks because forward returns overlap.

## Backtests and interpretation

Historical cost estimates were explicitly authorized for this research:

```powershell
quant/.venv/Scripts/python.exe -m quant.pipeline.run_backtest --from 2016-01-01 --to 2026-11-09 --estimate-historical-costs
```

Monthly close signals execute at the next exchange-session open. The initial
portfolio holds up to 25 stocks, enters above percentile 90, exits below 35,
uses capped inverse volatility (5% per stock), and retains unallocatable cash.
Targets may drift between rebalances. Fractional split-adjusted units are used.
Missing or suspended opens produce recorded skipped orders, never future fills.
Missing holding valuations stop the run and require verified settlement or
delisting evidence; the simulator does not silently discard a losing security.

The preserved baseline uses **price returns**, excluding cash dividends. Add
`--total-return` to credit gross cash dividends on the ex-date, before open orders,
to positions held at the previous close. Ex-date buyers receive no dividend;
ex-date sellers retain the entitlement. Cash per raw share is converted to the
simulator's split-adjusted units. Cash is not automatically reinvested. Actual
payment lags and withholding taxes are excluded by this research convention.
Total-return runs require complete official Nifty 50/Nifty 500 TRI history and
prefer TRI for metrics; price benchmarks remain secondary. TRI is close-only: its
first return uses the preceding session close, with no invented open. Factor V1
features and 63-session IC labels retain their frozen **price-return** definitions.
Consequently those IC diagnostics do not claim total-return predictive accuracy. Sharpe uses zero risk-free return and Sortino uses a zero minimum
acceptable return; both assumptions are recorded in every run. These results do
not establish investment value. Nifty 50 and Nifty
500 are gross index comparisons; liquid equal weight, 12-1 momentum top-25
and inverse-volatility baselines share next-open execution and transaction costs.
The baseline population is independent of Factor V1 feature completeness.

The cost model separates brokerage, delivery STT, exchange/IPFT charges, SEBI
fees, service tax or GST, stamp duty, DP charges, slippage and market impact.
`cost-schedule.json` exports effective dates (exclusive end), product, side,
charge type, rate type, rate, source reference and verification for every input.
Schedules include the June 2016 service-tax change, July 2017 GST transition,
July 2020 buyer-only stamp duty, and exchange-fee eras. Source-backed exchange
schedules cover October 2024 onward. Brokerage, DP, slippage and market impact
remain explicit research assumptions. DP is charged per instrument sale day.

Earlier eras require `--estimate-historical-costs` and retain
`cost_status=HISTORICAL_COST_PROXY`: broker volume slabs, historical SEBI fees,
state stamp arrangements and broker contracts have not all been verified.
Individual known tax changes do not certify the whole schedule. Proxies begin in
2016; there is no arbitrary-date modern-rate fallback. A custom unverified
schedule also requires opt-in. No proxy-cost run can pass production validation.

Primary references: [NSE delivery STT circular](https://nsearchives.nseindia.com/content/circulars/FATAX63809.pdf),
[NSE October 2024 fees](https://nsearchives.nseindia.com/content/circulars/FA64232.pdf),
[NSE March 2026 fee split](https://nsearchives.nseindia.com/content/circulars/FA73061.pdf),
[NSE levy guidance](https://www.nseindia.com/static/invest/first-time-investor-sebi-turnover-fees-stt-other-levies),
[IPFT and GST](https://support.zerodha.com/category/account-opening/resident-individual/ri-charges/articles/ipft-charges),
[DP baseline](https://support.zerodha.com/category/account-opening/resident-individual/ri-charges/articles/what-do-dp-charges-mean).

Each unique directory under `data/artifacts/backtests/factor_v1/` contains
config, metrics, curve, trades, holdings, skipped orders, IC, deciles, rolling
excess returns, benchmark comparisons, block-bootstrap IC intervals, robustness
results and a Markdown report. Config records git revision, source-code hashes,
input-file hashes, dependencies, model/feature/cost versions, seed, date range,
universe and portfolio settings. Feature manifests are checked again before
ranking. Preserve raw archives and normalized input snapshots with these hashes
when retaining a run; hashes alone do not recreate deleted input bytes.

Walk-forward artifacts are separate six-year-train/one-year-test windows starting
in 2016. Training labels are purged and embargoed by 63 sessions. V1 weights are
predeclared, so the training set does not fit or optimize parameters. The final
year is truncated to the available data. Robustness covers 1.5x/2x costs and
slippage, 20/25/30 holdings, INR 25/50/100 million ADV, and nearby momentum
lookbacks. Variants are not selected using test outcomes. `--skip-robustness`
is exploratory and cannot pass the stress hurdle.

Evidence reports assess OOS excess, IC, monotonic deciles, after-cost return,
stress survival, yearly concentration, turnover, IR and Sharpe, coverage and all
five baselines. Sector concentration remains unassessed until historical
point-in-time classifications exist. Return clusters provide a separate PIT
diagnostic: 252 trailing session returns, correlation distance sqrt(2(1-rho)),
single-link hierarchical clustering cut at distance 1.0. Membership is local to
each signal date. Actual holdings produce maximum cluster weight, cluster count,
effective cluster count and unknown weight. Missing histories stay unassessed.
The initial 40% maximum cluster weight is diagnostic and does not change holdings.
Evidence is split into STATISTICAL_SIGNAL, ECONOMICALLY_VIABLE and
PRODUCTION_VALIDATED. Economic checks include a declared 40% drawdown ceiling.
Production additionally requires verified costs, assessed PIT diversification,
PIT data, completed forward testing and immutable recommendation history. The
existing combined research hurdle remains available; public recommendations and
ML promotion remain disabled. `NOT_VALIDATED` may mean failed or
unmeasurable criteria; inspect the individual checks. V2 fundamentals, Elastic
Net, paper trading, Mongo publishing and the `/quant` UI remain conditional on
the guide's evidence gates. None is enabled by an attractive backtest alone.

## Verified data limitation (2026-11-13)

The local build contains 8,417,222 adjusted-source rows over all 4,184 expected
sessions through November 12, 2026. Price and benchmark session coverage is 100%.
However, the original NSE bhavcopy CSVs through June 21, 2011 omit the ISIN column.
The first ISIN-bearing session is June 22, 2011. All 369 earlier sessions remain
unresolved: they are retained in raw/normalized history, but cannot enter a
resolved historical universe. A current identity table cannot repair this gap
without dated evidence. Window-aware research readiness now preserves the full
raw audit while accepting a later trustworthy signal window. Verified identity
coverage begins on June 22, 2011; the conservative 252-return warmup ends on
June 25, 2012. The local 2016+ window passed all readiness checks on November 13,
2026. Later identity gaps, corrupt data or a failed rebuild revoke readiness.
Data readiness does not imply validated model performance.

`audit_identities` writes a dated identity-coverage report with yearly row counts,
the affected sessions, and original archive URLs/SHA-256 values. NSE documents
symbol/series/ISIN masters in its [historical data specification](https://nsearchives.nseindia.com/content/press/Data_details_CM.pdf).
No verified historical master archive for these dates has been loaded. Recovery
requires authoritative effective-date mapping evidence. Using today's master or
backfilling the first future ISIN would introduce unsupported identity assumptions.
The complete 2010-present raw audit remains required. Early unresolved rows are
retained and excluded from eligible universes; this is not a historical ISIN backfill.


## Validation sequence and reproducibility

The current-fixes plan is staged. Finish the Factor V1 evidence before developing
Factor V2, Elastic Net, forward publishing or the quant UI. The local fundamental
audit currently has zero filings; no reliable PIT fundamental window is established.
The audit never treats filing counts alone as proof of universe-wide coverage.

```powershell
quant/.venv/Scripts/python.exe -m quant.pipeline.weekly_audit --to 2026-11-12 --rebuild-adjusted
quant/.venv/Scripts/python.exe -m quant.pipeline.check_research_ready --as-of 2026-11-12 --backtest-start 2016-01-01
quant/.venv/Scripts/python.exe -m quant.pipeline.audit_fundamentals
quant/.venv/Scripts/python.exe -m quant.pipeline.build_features --as-of 2026-11-12
quant/.venv/Scripts/python.exe -m quant.pipeline.run_factor_v1 --as-of 2026-11-12
quant/.venv/Scripts/python.exe -m quant.pipeline.backfill_tri --from 2015-12-01 --to 2026-11-12
quant/.venv/Scripts/python.exe -m quant.pipeline.run_backtest --from 2016-01-01 --to 2026-11-12 --estimate-historical-costs --total-return --hypothesis "Unchanged V1 with dated costs, cluster diagnostics and cash dividends"
```

Readiness reports expose raw start, observed verified identity start, first
possible signal session, requested start and identity gaps. Boundaries and the
default warmup live in `quant/boundaries.py`. Each successful full audit freezes
an integrity artifact under `data/research/integrity`. Subsequent feature/ranking
commands may reuse a proof only after cryptographic verification of the complete
input inventory, relevant pipeline state, gate source files and dependencies.
A changed, added or deleted partition invalidates it. The explicit readiness CLI
always performs a fresh full audit.

Full rebuilds flush raw identity buckets in small row groups, disable insertion
order preservation, bound DuckDB memory/spill and release consumed scratch
inputs as adjusted output grows. Use a data drive with sufficient working space.
Recomputed partitions with exactly equal contents are not rewritten. A partial
or failed rebuild keeps readiness revoked. Frozen inputs should be preserved
with the corresponding source snapshot, rather than relying on a git hash alone.

Every research attempt freezes model/feature versions, weights, universe,
portfolio and run parameters before the readiness gate. The append-only
`data/research/experiments.csv` records both STARTED and final outcome events
under the same experiment ID, including blocked attempts. Immutable run JSON
lives under `data/research/experiments`. Supply an explicit `--hypothesis` for
later experiments. Do not tune after viewing the first result.

Official TRI provenance is archived under `data/raw/nifty_indices/tri`; normalized
history is separate in `data/normalized/index_tri`, never mixed with price indices.
Yearly downloads must exactly match the official exchange calendar before
publication. Source: [Nifty Indices historical data](https://niftyindices.com/reports/historical-data).
Historical indirect-tax references: [CBIC stock-broking FAQ](https://cbic-gst.gov.in/sectoral-faq.html),
[Government KKC history](https://ies.gov.in/arthapedia/concept/krishi-kalyan-cess-kkc),
and [NSE April 2023 charges](https://nsearchives.nseindia.com/content/circulars/FA56129.pdf).


On this workstation, C: ran out of working space during the full-history rebuild.
A separate working copy was created at `D:/Market_Pulse_Quant_20261113/data` and
`QUANT_DATA_DIR` in the local root `.env` was updated to that path. The original
C: data and original frozen baseline inputs were retained. This is local setup;
no D: dependency is hardcoded in the application or package defaults.


The first original 2016+ baseline stopped at ESSAROIL on February 10, 2016:
its held ISIN had no quoted bar after February 9. The failure is retained in the
experiment ledger and frozen baseline archive. An official
[exchange-filed exit letter](https://www.bseindia.com/xml-data/corpfiling/CorpAttachment/2016/2/0A5854E1_0389_40E7_8D3E_685DC087DF90_165210.pdf)
confirms the suspension/delisting and a conditional tender offer. A cash offer is
not evidence of an automatic payment date or an executable exchange fill. Full
OOS portfolio conclusions remain blocked until PIT lifecycle and settlement
accounting can value held delistings without invented exits or retrospective
exclusions. The first snapshot's top 30 passed their checks, but a wider review
found 55 fund units among 493 ranked EQ instruments. The stock-only universe fix
preserves that snapshot in revisions and bumps the feature version.


## November 17 audit implementation

The audit document describes a gated roadmap, rather than authorization to skip
research evidence. Factor V1 weights, lookbacks and portfolio defaults remain
frozen. V2, ML, forward publishing and the UI remain gated.

Implemented in this pass:

- Discovery under all of `quant`, Python 3.12 CI with checkout/setup-python v7,
  dependency validation, and syntax compilation. The required job name is
  `Quant unit tests`. Live source tests remain manual.
- Windows extended paths for atomic artifact writes, removal of duplicate test
  definitions, compounded yearly excess-return concentration, and explicit
  `QUANT_BROKER_PROFILE=GENERIC_ZERO_DELIVERY`. Other broker profiles fail closed.
- Official lifecycle inventory discovery, immutable raw archives and reviewed
  circular import with SHA-256 validation. Inventory downloads alone remain
  `NEEDS_REVIEW`: current lists do not establish historical announcement timing.
- Lifecycle schema, timezone-aware publication checks, PIT state transitions,
  universe entry flags, daily next-open risk exits, mandatory cash settlements,
  and mandatory successor conversions in raw-share units. Missing valuations
  still block. No forward-filled prices, inferred tender participation or
  undocumented zero recoveries are introduced.
- Lifecycle events and policy/scenario metadata in full research, baselines,
  robustness, walk-forward and manifests. Adding lifecycle evidence invalidates
  an earlier feature manifest. Feature version is `factor_v1_features_1.0.2`.
- An ESSAROIL fixture tied to the checksum of the official February 16, 2016 exit
  letter. Its publication cutoff conservatively uses document-day end. The
  letter does not prove the January notice's publication timestamp, and the
  optional INR 262.80 offer does not establish automatic payment. Earlier
  information must come from separately verified contemporary notice evidence.

Operations:

```powershell
python -m quant.pipeline.backfill_lifecycle --refresh-lists
python -m quant.pipeline.backfill_lifecycle --events-json reviewed-events.json
python -m quant.pipeline.update_lifecycle --events-json additional-events.json
```

Reviewed JSON is a list of schema records from `lifecycle_normalize.py`, including
an official `source_url`, the reviewed document's `source_sha256`, a stable
instrument identity, timezone-aware `announced_at`, and effective/economic terms.
The importer downloads and archives the document, verifies its bytes, and fills
raw provenance. Existing event IDs cannot be overwritten. Publication timing is
never substituted with the download timestamp.

The default `KNOWN_EVENT_NEXT_OPEN_EXIT` scenario applies deterministic risk exits
plus documented mandatory economics. `MANDATORY_ONLY` disables proactive risk
exits for sensitivity analysis. Optional offer participation and hypothetical
zero recovery are deliberately rejected until their independent assumption and
execution policies exist. Both scenarios retain the investability overlay.

Operational gates still require verification outside unit tests: authenticated
GitHub branch protection for the `Quant unit tests` check, a green remote run,
live-source smoke tests, reviewed lifecycle coverage, the full historical audit,
and frozen price/total-return OOS runs. No V1-complete or production-validation
claim follows merely from implementing the lifecycle engine. Historical cost
proxies still prevent production validation. Do not start V2 or ML while these
gates remain unmet.


Local validation on November 17: 190 non-integration tests passed, all 11 live
integration tests passed after the NSE origin migration fix, `pip check` passed,
and syntax compilation passed. Six official lifecycle inventories were archived
(14 proposed, 460 delisted, 12 voluntary applications, 15 progress rows, and two
suspension lists with 36 and 1 rows). These counts describe downloaded rows, not
verified PIT lifecycle coverage. Branch-protection update returned HTTP 401
because no authenticated GitHub API session was available.
