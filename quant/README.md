# Quant data foundation and Factor V1 research

This package is independent of the Next.js application. It collects free source
data, constructs historical eligible universes, ranks stocks with a fixed Factor
V1 model, and runs local research simulations. It does not publish recommendations
or place orders. A working research engine does not establish investment value.


## Current status

See [CURRENT_STATUS.md](CURRENT_STATUS.md) for current versions, CI and operational blockers.
Earlier phase documents are historical snapshots.

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

`update_all` runs calendar, market EOD, corporate actions, lifecycle refresh/audit, adjusted OHLC,
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
`--total-return` to credit gross cash dividends on the ex-date, after open orders,
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


## November 17 audit implementation (policy 1.0.0 history)

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
  an earlier feature manifest. See `quant/version.py` for current versions.
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

The primary baseline is `MANDATORY_ECONOMIC_EVENTS_ONLY`; `MANDATORY_ONLY` is its
alias. `KNOWN_EVENT_NEXT_OPEN_EXIT` additionally exits dated risks at the next
executable open. All scenarios retain the investability overlay. Explicit
`FORMAL_EXIT_OFFER_PARTICIPATION` requires an optional offer with a documented
price, deadline and settlement date, and shares held by the deadline. It cannot
bridge an unvalued suspension interval. `ZERO_RECOVERY_STRESS` explicitly records
unvalued holdings as hypothetical write-offs; it supplies no recovery evidence.

Operational gates still require verification outside unit tests: authenticated
GitHub branch protection for the `Quant unit tests` check, a green remote run,
live-source smoke tests, reviewed lifecycle coverage, the full historical audit,
and frozen price/total-return OOS runs. No V1-complete or production-validation
claim follows merely from implementing the lifecycle engine. Historical cost
proxies still prevent production validation. Do not start V2 or ML while these
gates remain unmet.


Local validation on November 17: 192 non-integration tests passed, all 11 live
integration tests passed after the NSE origin migration fix, `pip check` passed,
and syntax compilation passed. Six official lifecycle inventories were archived
(14 proposed, 460 delisted, 12 voluntary applications, 15 progress rows, and two
suspension lists with 36 and 1 rows). These counts describe downloaded rows, not
verified PIT lifecycle coverage. Branch-protection update returned HTTP 401
because no authenticated GitHub API session was available.

The original NSE ESSAROIL announcement was subsequently retrieved and archived
from the official corporate-announcements API (exchange sequence `100409001`,
announcement timestamp January 27, 2016, 18:24 IST). A separate fixture now proves
that an existing holding exits at the January 28 open, while future entry is
blocked; no tender payment is assumed. The verified suspension and exit-offer
records were imported into the configured local research dataset. This resolves
the evidence needed for this security's risk overlay; it does not certify full
historical lifecycle coverage or a completed OOS result.

The implementation commit is local. A non-interactive push failed because no
GitHub credentials were available. Remote CI and branch protection must be
verified after authentication is restored; historical baseline and later stages
remain gated until then.

The completion and forward-testing implementation, current operational blockers,
and commands are documented in [PHASE_V1_STATUS.md](PHASE_V1_STATUS.md). The new
paper pipeline accepts completed, checksummed price and total-return baselines,
freezes signals before the next exchange open, reuses historical accounting,
and appends matured outcomes separately. It never backfills forward signals.

The subsequent evidence/fundamental-foundation phase is described in
[NEXT_PHASE_STATUS.md](NEXT_PHASE_STATUS.md). Clusters use 252 trailing sessions
with at least 220 overlapping observed returns per pair, never filled prices;
insufficient history/overlap is explicit. Ranking exports reproducible top,
bottom and middle review samples. A sealed `v1-decision.json` separates the next
research decision from production certification; forward launch requires both
positive baseline decisions and resolved held-event accounting. Completion seals
cannot be overwritten to bless changed artifacts. Fundamental backfill,
universe-level coverage, PIT snapshots and historical-share reconstruction are
evidence infrastructure; Factor V2 remains disabled.

## Fresh NSE source diagnostics

Run `python -m quant.pipeline.probe_nse_source` to make a fresh calendar smoke
request using the configured transport. `--data-dir <directory>` selects where
raw responses and reports are archived. Each invocation writes a unique report
under `reports/source-probes/`, including source hashes, transport settings,
HTTP status and provenance. A successful HTTP response must also parse as a
calendar containing at least five holidays. This diagnostic does not replace
the full live suite or certify research readiness.

The command exits zero for `LIVE_SMOKE_PASSED` and one for
`LIVE_SOURCE_UNAVAILABLE`. It never uses cached successes. Authorization retries
honor `Retry-After` before the single permitted session renewal; cooldowns above
60 seconds stop the operation for a later retry. Small randomized delays
preserve the configured minimum interval between requests. Persistent HTTP 403
responses remain failures.

## Offline multifactor research

Install `python -m pip install -r quant/requirements-research.txt` for constrained
risk research. V1 retains its original dependencies and scoring behavior.
Ledoit-Wolf covariance is implemented using NumPy moments; the optimizer uses
SciPy. Optional Elastic Net training remains gated off until V2 evidence passes.

Offline development and archived-data replay can proceed while a source or V1
evidence gate is unresolved. Completion seals, real forward launch and promotion
retain their evidence prerequisites. No model switch is enabled by these tools.

`quant.pipeline.reparse_fundamentals` reads the source corpus without changing it
and emits a unique replay directory, parsed filings, metadata/document hashes,
implementation hashes and review results. For example:

```powershell
python -m quant.pipeline.reparse_fundamentals --source-data-dir D:/Market_Pulse_Quant_20261113/data --data-dir data/major-phase-execution --from 2024-01-01 --to 2026-11-17 --limit 250
```

Use `--offset` for subsequent archived-document batches. This is a parser replay,
not proof of historical coverage. `quant.pipeline.acquire_fundamentals_stage1`
downloads unattempted documents from existing discovery metadata in finite
checkpointed batches. It stops on source failure or a batch parsing rate below
80%. `--batch-size` defaults to 100 (maximum 250); `--max-batches` defaults to
one (maximum 250). It never expands before 2024 automatically. Progress is
written to `reports/fundamental-stage1-acquisition.json` in the configured data
directory. Run only one supervisor for the same date range at a time.

The taxonomy registry accepts reviewed namespace/concept combinations and
explicit consolidation declarations. Conflicting quarter/YTD reporting dates,
segment dimensions, conflicting values and incorrect units stay unusable.
`BANKING_` and `NBFC_INDAS_` are explicit exchange-document family prefixes;
NSE's `bank="B"` metadata code is recognized. A taxonomy family does not certify
all company inputs. For example, currency-tagged bank ROA is rejected rather
than converted into a ratio. Current industry classifications are never applied
backward by this parser.

`quant.pipeline.build_fundamental_features` builds research inputs from dated
raw-price keys, verified archived filings, share anchors, capital events and
share-coverage evidence. Its explicit paths are `--price-keys`, `--filings`,
`--anchors`, `--capital-events`, `--share-coverage` and `--output`; `--data-dir`
must identify the corpus containing the original filing archives. Outputs cannot
replace earlier feature files. Share coverage requires instrument ID,
`covered_from`, `covered_through`, timezone-aware `known_at`, `VERIFIED` status
and a source SHA-256. An anchor must precede the signal and lie within that
verified coverage interval.

The initial candidate uses these equal-weighted within-block inputs:

| Block | Industrial | Bank |
| --- | --- | --- |
| Quality | Annual PAT / average equity; CFO / positive PAT; negative debt / equity | Annual PAT / average assets; PAT / average equity; negative gross and net NPA / advances |
| Growth | Comparable quarter revenue and positive-base PAT YoY | Deposit and advance YoY |
| Value | Annual earnings, FCF and equity / dated market capitalization | Annual earnings and equity / dated market capitalization |

Annual averages require comparable then-known annual statements. Growth uses
quarter-only facts or comparable cumulative differencing; it never sums YTD
statements. Negative or absent growth denominators remain missing. All declared
inputs in a company's applicable blocks are required. Unsupported financial
families remain outside the initial V2 scoring population. Value requires
verified historical shares and raw contemporaneous prices. No current-share
backfill or missing-block weight redistribution is performed.

`quant.models.factor_v2.same_universe_scores` returns full V1, covered V1 and V2.
Covered V1 normalization is recalculated on the exact dated V2 population. The
initial V2 uses seven equal block weights, 1%/99% winsorization, median/MAD
standardization clipped to +/-3, and at least 20 names per dated entity group.
V1's existing price/risk/liquidity block formulas are retained.

Copy `quant/research/v2-spec.template.json` to a new specification, declare
nonoverlapping evaluation windows and review the candidate formulas, thresholds
and capital assumptions before setting its review fields. The supplied template
is a draft; its acceptance numbers are proposed research defaults. Freeze the
reviewed specification with:

```powershell
python -m quant.pipeline.freeze_v2_specification --spec reviewed-v2.json --output frozen-v2.json
```

The freeze includes implementation hashes. A code change requires a newly
reviewed freeze. `quant.pipeline.run_factor_v2_research` requires `--spec`,
`--price-baseline`, `--total-return-baseline`, `--filings`, `--anchors`,
`--capital-events`, `--share-coverage` and `--output-root`. It verifies both V1
seals/decisions, source integrity, archived filings, and every dated 80% overall /
90% liquidity coverage cutoff before simulations. Feature completeness is gated
separately. The shared engine produces all three comparison arms, IC/deciles,
factor IC by year/rolling observations, 1.5x/2x cost stress, accounting ledgers,
an explicit decision and an immutable seal. A blocked attempt retains its
outcome and has no seal. `PRICE` is the draft default; `TOTAL_RETURN` uses the
dividend ledger and Nifty 500 TRI consistently. Portfolio capital and estimated
historical charges are recorded; a research decision never certifies production.

`quant.pipeline.run_portfolio_risk_research --v2-experiment <sealed-directory>
--spec <frozen-risk-specification> --output-root <directory>` requires a passing
V2 research decision and explicitly reviewed capital. It compares simple
rank-selected inverse volatility with the declared 12% and 15% targets. Trailing
covariance uses 252 sessions with at least 220 jointly observed returns and no
filling. Position, cluster, gross, volatility and target-order capacity limits
are checked; realized next-open capacity violations block completion. Cash is
allowed and infeasible allocations fail closed. The simulator's optional risk
callback receives prior-close marks/NAV; V1 callbacks keep their existing API.

`quant.research.purged_cv` supplies expanding and nested date-based splits and
date-balanced weights. Label exits must mature before the training cutoff and
embargo. No Elastic Net is fitted, promoted or assigned nonzero weight merely
because these utilities are implemented.
# Evidence and champion/challenger operations

Current phase assessment and remaining evidence gates are in
[EVIDENCE_PHASE_STATUS.md](EVIDENCE_PHASE_STATUS.md). Existing V1 weights and
blocked experiments are preserved. Historical archive readiness and live API
health are separate; a calendar HTTP 403 does not certify or revoke archive
checksums. Forward refresh still requires the latest required exchange session.

These commands use the configured corpus unless `--data-dir` is supplied.
Use a real certified session for `--to`; November 17 below is the retained
certified cutoff, not an assumption that later data is ready.

```powershell
python -m quant.pipeline.certify_implementation
python -m quant.pipeline.validate_source_health --to 2026-11-17 --backtest-start 2016-01-01
python -m quant.pipeline.report_fundamental_acquisition --from 2024-01-01 --to 2026-11-17
python -m quant.pipeline.audit_share_history_coverage --from 2024-01-01 --to 2026-11-17 --universe <dated-universe.parquet> --anchors <anchors.parquet> --capital-events <events.parquet> --share-coverage <coverage.parquet>
```

Share anchors, capital events and completeness evidence need `raw_path` and
`source_sha256` referencing checksum-verified archives under the data directory.
Verified flags and current share counts alone are insufficient. Both filing
and share certification require 12 consecutive passing monthly cutoffs and
80% overall / 90% top-100 ADV coverage. Every subsequent cutoff must pass too.

A data-window fallback is conditional on documented exhaustion for every
mandatory held blocker. Its input is a JSON list of audits containing
`event_id`, `mandatory_held_event=true`, `boundary_date`,
`status=EVIDENCE_EXHAUSTED_UNRESOLVED`, `sources_checked`, `dates_checked`,
`documents_checked`, `search_completed_at`,
`reason_transition_cannot_be_certified`, `reviewed_by`, `reviewed_at`,
`missing_facts`, `evidence_hashes` (archive-relative path to SHA-256), `conclusion`,
`performance_used_to_decide_exhaustion=false` and
`performance_used_to_choose_start=false`. The current TIDEWATER
search is ACTIVE and cannot supply this input. Once permitted:

```powershell
python -m quant.research.evaluation_window --from 2016-01-01 --to <certified-date> --search-audit <reviewed-audits.json> --warmup-sessions 252 --output <new-window.json>
python -m quant.pipeline.run_backtest --from 2016-01-01 --to <certified-date> --evaluation-window <new-window.json> --estimate-historical-costs
python -m quant.pipeline.run_backtest --from 2016-01-01 --to <certified-date> --evaluation-window <same-window.json> --estimate-historical-costs --total-return
```

`quant/specs/factor_v2_1.0.0.json` is a DRAFT policy proposal, not a reviewed OOS
result. After certifying data continuity, declare `evaluation_windows`, record
the actual review, and use `freeze_v2_specification`. The frozen envelope hashes
policy and implementation. A specification store reserves one policy per
`spec_version`; post-result policy edits require a new version. The V2 runner
uses the specified portfolio/cost/risk settings for all four arms and runs all
declared capital scenarios. It emits block missingness, factor evidence and
correlations, per-cutoff filing/share/feature coverage, risk budgets,
target/fill ledgers, cost stress and the V2 decision before sealing.

Model lifecycle commands accept explicit files; no model is validated merely
by registration:

```powershell
python -m quant.pipeline.register_model_candidate --registry <registry-dir> --card <model-card.json>
python -m quant.pipeline.promote_model --registry <registry-dir> --model-id <id> --state RESEARCH_CANDIDATE --reason <recorded-reason>
python -m quant.pipeline.promote_model --registry <registry-dir> --model-id <id> --state HISTORICALLY_VALIDATED --reason <recorded-reason>
python -m quant.pipeline.promote_model --registry <registry-dir> --model-id <id> --state FORWARD_CHALLENGER --reason <recorded-reason>
python -m quant.pipeline.run_registered_forward --registry <registry-dir> --model-id <id> --cohort <new-name> --as-of <actual-signal-session> --price-baseline <sealed-price> --total-return-baseline <sealed-total-return>
```

Cards contain all provenance fields in `quant/models/model_card.py`, plus
`historical_experiment` and `historical_completion_sha256` for validation.
For V2, `spec_hash` is the canonical `content_hash` of the inner specification;
`data_manifest_hash` hashes the experiment's `manifest`, including new V1 runs.
New V1 cards hash the sealed `specification.json`, which preserves the original
pre-run `frozen-baseline.json`. Legacy configs without a manifest use their
`files` object. Model versions, feature versions, policies and
sealed decisions must agree. Forward V2 also requires `--spec`, `--filings`,
`--anchors`, `--capital-events`, and `--share-coverage`. Registered stores are
under `forward/registered/<model-id>/<cohort>/`; existing V1 stores are retained.
Run the registered command each real signal session after the data refresh;
it freezes that session, replays the shadow and appends matured 21/63 outcomes.

Use `report_forward_comparison --v1-root ... --v2-root ... --to ... --output ...`
for matched-date cohorts. `report_research_monitoring --help` lists the dated
feature, IC, NAV and observation inputs. Observation JSON contains
`source_health`, fractional `coverage` (`overall`, `top100`, `parser_attempts`,
`parser_failures`) and fractional `cluster_weights`. Supply `--incident-root`
and the cohort's `--model-id`; the journal supplies assessed incident counts.
IC inputs include `block`,
`IC` and `exit_date`; features include `as_of`, and NAV includes `trade_date`.
The reference feature window must precede the current window. Unassessed
dimensions cannot pass monitoring; alerts never retrain.

Champion promotion additionally needs a frozen card `forward_policy` with at
least 126 signal sessions, 6 rebalance cycles and 30 distinct matured
63-session signals. Supply `--forward-root`, `--monitoring-report`, `--reviewer`
`--manual-record` and `--incident-root`. The monitoring report must bind the
current incident-journal hash, with zero unresolved incidents. The manual record identifies `model_id`,
`model_card_sha256`, `monitoring_sha256`, `reviewed_by`, `reviewed_at`,
`decision=PROMOTE` and a reason. Retire an existing champion before promoting
another. No production publishing is enabled by these commands.

Elastic Net remains gated and has zero weight until real V2 historical PASS
and stable multi-year PIT features permit the optional workstream.

Earlier historical acquisition examples additionally require
`--expansion-decision <reviewed-decision.json>` when starting before 2024. The
record identifies `decision=EXPAND`, `prior_stage`, `next_stage`, `reviewed_by`
and timezone-aware `reviewed_at`, plus `acquisition_report`, `coverage_report`
and `share_report`, each containing `path` and `sha256` for verified reports
inside the data directory. The previous stage must have no unattempted or
retryable candidates and certified monthly filing/share continuity.

## Evidence closure and model selection

The section-by-section implementation assessment and actual blockers are in
[EVIDENCE_CLOSURE_STATUS.md](EVIDENCE_CLOSURE_STATUS.md). All commands below
write to explicit destinations or the configured data directory; use
`--data-dir` when collecting a separate local operational snapshot.

`certify_implementation --unit-results <unit.xml> --live-results <live.xml>`
records the full commit, clean-tree observation, exact-SHA CI URL/status,
local test count, dependency/compile/whitespace checks and independent live
failures. Unknown local counts remain null. Both V1 and V2 real historical
runners require clean exact-SHA unit certification. The CI workflow retains
JUnit evidence as `quant-unit-evidence`. NSE 403 failures stay visible without
revoking independently verified historical files.

Dataset observations can be supplied to `validate_source_health` using
`--dataset-observations <observations.json>`. Each row names `dataset`,
`source_id`, `source_class`, `status`, `provenance_verified`, and, for current
work, `verified_session`. Archived copies also require `checksum_verified`.
`quant/data/source_requirements.py` declares datasets for historical research,
forward refresh, fundamental acquisition and production publishing. Approved
official static files can satisfy the same dataset as an unavailable API.
The four health dimensions remain separate. No anti-bot bypass is introduced.

Run an attributable coverage audit before planning acquisition:

```powershell
python -m quant.pipeline.audit_fundamental_coverage --from 2024-01-01 --to <certified-session> --universe <dated-universe.parquet> --attempts <checkpoint.json> --share-validity <dated-share-validity.parquet>
python -m quant.pipeline.plan_fundamental_acquisition --universe <same-universe.parquet> --coverage <coverage.json> --filings <filings-snapshot.parquet> --attempts <checkpoint.json> --output <plan.json>
python -m quant.pipeline.acquire_fundamentals_stage1 --from 2024-01-01 --to <certified-session> --plan <plan.json> --batch-size 100 --max-batches 1
```

`--share-validity` is optional; absent evidence produces null share deficits.
Coverage gaps are percentage points, with separate integer name deficits.
Missing-name reasons cover unattempted, download, parser, timing, identity and
unsupported-entity failures. Candidate IDs and historical ADV bind the planner
to each cutoff. Priorities use potential marginal name-month repairs: top-100
gaps first, then proximity to 80%, consecutive months and bank/NBFC gaps.
Already planned repairs are discounted; future disclosures never repair an
earlier month. Estimates do not certify successful acquisition. Candidates
outside the plan remain eligible for later bounded batches. No return column
is used. Preserve and regenerate plans as the acquisition snapshot changes.

Acquisition reports retain legacy counters and add `candidate_count`,
`attempted_count`, `terminal_status_count`, `retryable_count`,
`unattempted_count`, `attempt_completion_pct`, `usable_document_pct` and
per-candidate `terminal_status`. Missing URLs are classified explicitly while
remaining unattempted. Retryable failures remain visible even though they have
a terminal classification for the current attempt. Neither terminal
classification nor parser success establishes PIT universe coverage.

Formal evidence-search audits can be preserved with
`record_evidence_search --audit <audit.json> --output <new-record.json>`.
Every referenced archive is checksum-verified. Exhaustion requires the full
review record above. The fallback loader uses `validated_data_window_1.2.0`;
it never modifies an original blocked experiment.

Freezing V2 now requires both certified reports:

```powershell
python -m quant.pipeline.freeze_v2_specification --spec <reviewed-policy.json> --coverage <filing-coverage.json> --share-coverage <share-coverage.json> --output <frozen-spec.json>
```

The envelope binds both reports, the full code SHA, source hashes and the
coverage-only date-selection declaration. Monthly percentages are rechecked;
twelve passing cutoffs must precede OOS and continuous coverage must span the
declared interval. Frozen source inputs are checked again at research entry.
The draft now includes absolute minimum IC/IR and minimum valid windows,
alongside improvement, turnover, drawdown, label and cost-stress thresholds.
These are proposals awaiting real review. Outcomes are `BLOCKED`,
`INCONCLUSIVE`, `NO_GO_V2` or `GO_FURTHER_V2_RESEARCH`; an insufficient sample
cannot be reported as a tested rejection. No Elastic Net fit is admitted yet.

Initialize the operational incident journal explicitly, then open or resolve
incidents from reviewable JSON files:

```powershell
python -m quant.monitoring.incidents --root <incident-ledger>
python -m quant.pipeline.open_research_incident --ledger <incident-ledger> --record <opening.json>
python -m quant.pipeline.resolve_research_incident --ledger <incident-ledger> --incident-id <id> --record <resolution.json>
```

An opening supplies `incident_class`, `severity` (LOW/MEDIUM/HIGH/CRITICAL),
`affected_models`, `affected_cohorts` (absolute cohort paths), `affected_dates`
(ISO dates) and `evidence`; `incident_id` is optional. An empty scope list means
all models/cohorts/dates. A resolution supplies `resolution`, `reviewer` and
`evidence`. Opening and resolution are separate immutable, chained events.
An absent journal remains unassessed. Monitoring, comparison and promotion
read current scoped incidents; model/risk incidents also block promotion.

Matched cohort comparison requires identical signal dates, assumptions,
market/event file manifests and next-session execution times. Reports retain
21/63-session outcomes, excess returns, rank IC, hit rate, Sharpe, IR,
drawdown, turnover, costs and cash, and add capacity, cluster and incident
assessments. Older records with absent diagnostics stay unassessed.

For a historically validated registry candidate:

```powershell
python -m quant.pipeline.build_research_release --registry <registry> --model-id <id> --output <new-release-directory>
python -m quant.pipeline.build_research_release --output <release-directory> --verify-only --data-dir <immutable-source-data>
```

The bundle includes the model card, policy, original completion seal, input
manifest, coverage/share reports, metrics, factor/risk evidence, environment
and checksums, plus an unchanged `source-experiment/` for independent seal
verification. Packaging refuses existing destinations and unvalidated models.
Verification works after relocation; the optional data directory additionally
verifies archived input bytes. Price-only V1 declares fundamental/share reports
NOT_APPLICABLE. No release or journal action promotes a model automatically.
# Coverage feasibility and Stage 1 replanning

The November 19, 2026 phase assessment is in
[DATA_COVERAGE_STATUS.md](DATA_COVERAGE_STATUS.md). Before acquiring more
documents, use the same dated universe, filing snapshot and attempt checkpoint
as the PIT coverage audit:

```powershell
python -m quant.pipeline.report_fundamental_coverage_ceiling --universe <universe.parquet> --coverage <coverage.json> --filings <filings.parquet> --attempts <checkpoint.json> --output <ceiling.json>
python -m quant.pipeline.plan_fundamental_discovery_expansion --universe <universe.parquet> --coverage <coverage.json> --ceiling <ceiling.json> --output <discovery-plan.json>
python -m quant.pipeline.plan_fundamental_acquisition --universe <universe.parquet> --coverage <coverage.json> --filings <filings.parquet> --attempts <checkpoint.json> --output <acquisition-plan.json>
python -m quant.pipeline.acquire_fundamentals_stage1 --from 2024-01-01 --to <certified-session> --plan <acquisition-plan.json> --batch-size 100 --max-batches 1
```

After **each** batch, parse and normalize the acquired observations, rerun the
PIT audit and ceiling, and rebuild the plan. Input hashes and acquisition-state
hashes reject stale reuse. Stage 1 freezes a candidate set; retryable failures
and unreviewed parser findings do not close the stage. Missing source URLs are
classified without pretending a download was attempted.

Shares require archived anchors, dated capital changes and complete event
interval evidence. `--filings` derives anchors from normalized paid-up equity
capital and contemporaneous face value; `--anchors` accepts explicitly prepared
anchors instead. Both require source hashes/raw paths under the data directory.

```powershell
python -m quant.pipeline.build_share_history --data-dir <data-root> --from 2024-01-01 --to <certified-session> --keys <dated-keys.parquet> --filings <filings.parquet> --capital-events <events.parquet> --share-coverage <intervals.parquet> --output <share-history.parquet>
python -m quant.pipeline.audit_share_history --data-dir <data-root> --from 2024-01-01 --to <certified-session> --universe <universe.parquet> --anchors <anchors.parquet> --capital-events <events.parquet> --share-coverage <intervals.parquet>
python -m quant.pipeline.plan_share_evidence --data-dir <data-root> --from 2024-01-01 --to <certified-session> --universe <universe.parquet> --anchors <anchors.parquet> --capital-events <events.parquet> --share-coverage <intervals.parquet> --output <share-plan.json>
```

Unknown shares remain `value_feature_valid=false`. A candidate anchor can
appear in the discovery plan while a missing complete event chain still keeps
its theoretical share-coverage ceiling at zero.

After pushing, certify the exact clean SHA using the local JUnit files:

```powershell
python -m quant.pipeline.certify_implementation --data-dir <report-root> --unit-results <unit-tests.xml> --live-results <live-tests.xml> --unit-ci-run-url https://github.com/DakshUbhadia/Market_Pulse/actions/runs/<run-id>
```

The public run URL is an optional REST-quota fallback. Certification checks the
full commit link and successful unit workflow on GitHub, archives the page
hash, and keeps live source failures separate. No abbreviated SHA, unrelated
workflow, failed run or dirty source tree can authorize real historical runs.

# Data completion and historical certification

The current assessment is [HISTORICAL_CERTIFICATION_STATUS.md](HISTORICAL_CERTIFICATION_STATUS.md).
Build the authoritative discovery ledger from matching snapshots:

```powershell
python -m quant.pipeline.build_fundamental_discovery_gap --universe <dated-universe.parquet> --coverage <coverage.json> --ceiling <ceiling.json> --filings <filings.parquet> --output <gap.json>
python -m quant.pipeline.discover_fundamentals_targeted --data-dir <workspace-output-root> --corpus-data-dir <retained-source-root> --universe <dated-universe.parquet> --coverage <coverage.json> --ceiling <ceiling.json> --filings <filings.parquet> --attempts <attempts.json> --calendar <certified-calendar.parquet> --identities <dated-identities.parquet> --max-instruments 25 --max-cells 100 --max-requests 25 --max-documents 25
```

Each call creates a new `research/discovery-batches/<id>/` with raw-response
references, selected cells, normalized filings, PIT coverage, ceiling, gap,
acquisition plan and attempt checkpoint. Pass that batch's combined
`filings.parquet`, `coverage.json`, `coverage-ceiling.json`, and `attempts.json`
to the next call. Supply `--previous-batch <batch-report.json>` (repeatable)
to skip verified completed queries and continue bounded discovery. Changed
archives or missing previously discovered observations invalidate reuse.
NSE HTTP 403 stops its route and remains visible; it does not certify absence.

Optional `--fallback-manifest <reviewed-sources.json>` is a list of filing
metadata records. Each includes `instrument_id`, `symbol`, `period_start`,
`period_end`, `period_type`, `standalone_or_consolidated`, `source_type`
(`BSE_OFFICIAL` or `ISSUER_IR`), `source_exchange`, `source_url`,
`exchange_disseminated_at`, `reason_primary_source_unavailable`,
`dissemination_evidence_path`, `dissemination_evidence_sha256` and
`dissemination_reviewed_by`. Dissemination evidence bytes must be under the
output data root. BSE additionally requires `cross_listing_verified=true`
and `bse_security_code`. Issuers require `--issuer-host <reviewed-host>`,
`issuer_host_reviewed_by` and `reason_exchange_archive_unavailable`.
Use the preserved historical timestamp; retrieval time is never a substitute.
Document downloads and failed HTTP responses retain immutable raw bytes.

Create a capital-event ledger from explicit dated evidence, or bootstrap
review candidates from the official retained corporate-action corpus:

```powershell
python -m quant.pipeline.build_capital_event_ledger --data-dir <data-root> --events <capital-events.parquet> --output <ledger.parquet>
python -m quant.pipeline.build_capital_event_ledger --data-dir <workspace-output-root> --corporate-actions-root <retained-source-root> --output <candidate-ledger.parquet>
```

The bootstrap copies/checksums referenced official bytes into the output
root. It does not infer capital-effective dates from ex-dates, actual credit
from proposal deadlines, or historical dissemination from current retrieval.
All bootstrap rows require review. Complete event intervals are separate inputs.

Certified share history requires two distinct known anchor dates, every
material intervening event, complete interval evidence through the cutoff,
and reconciliation of each later reported count. Events after the final
anchor need another anchor. Issuance/buyback/conversion terms must explain
changes; an asserted `shares_after` cannot force reconciliation. Ambiguous
same-day actions require a reviewed composite row. Unknown terms, lineage
conflicts and mismatches leave Value invalid. The low-level legacy replay
helper is not a certification API; use `share_history` / `build_share_history`.

Successful implementation certificates are archived as
`reports/implementation-certification-<short-sha>.json`. The current report
records absolute JUnit paths and hashes. Preserve those bytes for subsequent
historical runner verification. A new SHA or changed source requires a new
certificate and reviewed frozen research specification.

## Historical evidence and forward validation

The current 43-section implementation assessment and outstanding research gates
are in [HISTORICAL_FORWARD_VALIDATION_STATUS.md](HISTORICAL_FORWARD_VALIDATION_STATUS.md).
All commands below use an environment installed from
`quant/requirements-research.txt`. In this checkout, `.venv/Scripts/python.exe`
contains the complete research dependencies.

An evidence-only evaluation declaration can be prepared automatically. It is
**ineligible for final research** until an independent human confirms transition
exhaustion and separately admits the exact declaration. The old 1.1 declaration
must be regenerated with the same evidence/calendar under policy 1.2; it cannot
be passed through as an approved window.

The prepared forms and complete source packet are in
`quant/artifacts/historical-forward-validation/reports/security-transitions/`.
`tidewater-2016-human-review.json` is intentionally pending. A human completes
the fields, sets `subject_id` to `TIDEWATER_2016`, sets `status` to `APPROVED`
for confirmation or `REJECTED` for reopening, supplies a reason and chooses
`CONFIRM_EVIDENCE_EXHAUSTED_UNRESOLVED` or `REOPEN_SEARCH` without using returns.
The `automated_review_sha256` and `subject_sha256` bind the canonical audit body;
the packet separately records the original audit-file digest. Save a completed
input under a new filename, then publish a new immutable record:

```powershell
python -m quant.governance.review --review completed-human-review.json --output data/historical-forward-validation/reports/security-transitions/tidewater-2016-human-review-confirmed.json
python -m quant.governance.review --review completed-window-review.json --output data/historical-forward-validation/reports/window-human-admission.json
python -m quant.pipeline.admit_evaluation_window --declaration data/historical-forward-validation/reports/v1-evaluation-declaration.json --transition-review data/historical-forward-validation/reports/security-transitions/tidewater-2016-human-review-confirmed.json --window-review data/historical-forward-validation/reports/window-human-admission.json --output data/historical-forward-validation/reports/v1-evaluation-window-admitted.json
```

The window review type is `EVALUATION_WINDOW_ADMISSION`, decision `ADMIT` or
`REJECT`, and its subject is supplied in `evaluation-window-admission-request.json`.
Its `subject_id` is `V1_FALLBACK_2017_03_28`. Use `APPROVED` for admission or
`REJECTED` for rejection. After recording an actual human transition decision,
update the gate journal with `python -m quant.governance.gates --data-dir
data/parallel-evidence-completion --review completed-immutable-human-review.json`.
The separately admitted declaration must be saved as
`reports/v1-evaluation-window-admitted.json` under that same data directory.
Review timestamps must follow the declaration and exhaustion review. All typed
reviews record human name/role, independent-review attestation, reason, explicit
performance-information use and a past timezone-aware timestamp. Model promotion
may consider performance; pre-OOS admission/approval may not. Checksums detect
changes; they do not authenticate a person's real-world identity. Never fill a
human's name or decision through automation.

Use the existing V1 command with the admitted artifact, unchanged factor and
portfolio settings, once exact-SHA certification and data readiness pass. Run
both PRICE and TOTAL_RETURN over the same approved dates and certified end.
The decision file retains its legacy `decision` field for registry compatibility
and adds `research_outcome`: `PASS_RESEARCH`, `NO_GO` or `INCONCLUSIVE`. Failed
prerequisites produce `BLOCKED` experiment outcomes. Research PASS permits
further testing only.

The current phase is `quant-parallel-evidence-completion`; see
[PARALLEL_EVIDENCE_STATUS.md](PARALLEL_EVIDENCE_STATUS.md). TIDEWATER remains
explicitly `PENDING`. The gate journal is hash chained and the prepared window
remains inadmissible until both human decisions are present. Pending and
rejected decisions have distinct metadata and never halt independent data work.

Initialize an isolated output workspace without changing the retained corpus:

```powershell
python -m quant.pipeline.prepare_parallel_phase --data-dir data/parallel-evidence-completion --review-evidence-root data/historical-certification
```

After certifying the exact current clean SHA, execute diagnostic PRICE and
TOTAL_RETURN runs using the original requested start and prepared declaration:

```powershell
python -m quant.pipeline.run_backtest --data-dir data/parallel-evidence-completion --corpus-data-dir D:/Market_Pulse_Quant_20261113/data --start 2016-01-01 --end 2026-11-17 --research-authority DIAGNOSTIC_ONLY --evaluation-window data/parallel-evidence-completion/reports/v1-evaluation-declaration.json --estimate-historical-costs
```

Repeat with `--total-return`. Diagnostic execution retains all source, lifecycle,
cost, robustness and walk-forward checks. It writes a separate integrity inventory
`diagnostic-completion.json`, never an accepted `completion.json`, historical
decision, registry admission or forward entitlement. A data failure still blocks
diagnostic completion. `outcome` separates governance, data, source and software
blocks. The declaration never becomes admitted through diagnostic execution.

Prepare draft seven-block inputs with `python -m quant.pipeline.prepare_v2_matrix
--price-features ... --fundamental-features ... --output ...`; missing verified
Value makes the full matrix `INCOMPLETE`. `quant.pipeline.run_v2_diagnostics`
requires an explicitly DRAFT spec and declared synthetic/archived diagnostic
scope. It exercises all four arms and capital scenarios without a real V2
decision. Neither data preparation nor a diagnostic success freezes a spec.

Build and verify portable diagnostic bundles with
`python -m quant.pipeline.build_diagnostic_release --source ... --output ...`.
The bundle is labelled `DIAGNOSTIC_RELEASE`, with historical validation,
promotion eligibility and real forward evidence all false. Its verifier works
after relocation. Research-release and registry verifiers reject it.

`quant.pipeline.run_test_forward.run_test_forward` runs controlled after-close
signal freezes, next-open shadow accounting and outcome tracking in
`forward/test-only/<cohort>`. `TEST_ONLY` propagates into signals, policies,
outcomes, monitoring and comparisons. Test and real cohorts cannot be mixed.
Synthetic evidence is never a substitute for 126 real signal sessions, six
rebalance cycles or 30 matured 63-session signals.

Capital-event verification is independent of event discovery:

```powershell
python -m quant.pipeline.verify_capital_events --data-dir data/historical-forward-validation --events reviewed-capital-events.parquet --output data/historical-forward-validation/reports/capital-events-verified.parquet
python -m quant.research.data_interval --filings filing-coverage.json --shares share-history-coverage.json --output data/historical-forward-validation/reports/v2-data-interval.json
```

Each event carries `event_evidence`, a dictionary (or JSON string) keyed by
`instrument_id`, `security_lineage_id`, `event_type`, `announced_at`,
`effective_date`, applicable `record_date`, `credit_date`, `listing_date` and
each supplied arithmetic term. Each fact proof contains its matching `value`,
`raw_path`, `source_sha256`, official `source_url`/`source_type`/`source_exchange`,
`reviewed_by` and `review_status=VERIFIED`. BSE/issuer proofs must meet the same
official-source admission policy. The summary row also retains archived source
bytes. A review flag without those bytes cannot yield `VERIFIED_COMPLETE`.

Share interval proofs retain the existing `covered_from`, `covered_through`,
`known_at`, source bytes and verification status, plus `interval_start`,
`interval_end`, `source_coverage` (archived relative-path to SHA-256 mapping),
`event_inventory_hash`, `unresolved_event_count=0`, `reconciled_start_anchor` and
`reconciled_end_anchor`. Use `event_inventory_hash` and `anchor_hash` from
`quant.data.capital_events` to bind the actual complete inventory and anchors.
An inventory digest is a binding, not a proof that all material events were
discovered; the reviewed source-coverage proof must establish that completeness.
Only complete events may change share counts. The optimistic share planner uses
temporary review assumptions solely for ceiling estimates and never saves them
as verified data.

The shared interval CLI exits nonzero and writes a `BLOCKED` report when coverage
is insufficient. V2 freeze requires that certificate and a typed human review:

```powershell
python -m quant.pipeline.freeze_v2_specification --spec reviewed-spec.json --coverage filing-coverage.json --share-coverage share-history-coverage.json --data-interval data/historical-forward-validation/reports/v2-data-interval.json --governance-review sealed-v2-human-review.json --output data/historical-forward-validation/research/frozen-v2.json
```

Compute the human review's subject with
`specification_subject(spec, coverage_reports, data_interval)` from
`quant.research.specification`. It binds the exact code SHA/source hashes, full
specification, both coverage hashes and shared interval. Review type is
`V2_SPEC_APPROVAL`, decision `APPROVE` or `REJECT`. Draft free-text reviewer
fields alone are insufficient. All seven blocks and the predeclared
10L/25L/50L/1Cr scenarios remain mandatory.

`discover_fundamentals_targeted` accepts reviewed official static/XBRL/direct
NSE URLs in `--fallback-manifest`, followed by verified BSE and reviewed issuer
sources. Every source needs a dated instrument identity and original period /
statement metadata. Historical availability uses `exchange_disseminated_at`,
`dissemination_evidence_path`, `dissemination_evidence_sha256` and
`dissemination_reviewed_by`; missing proof is recorded as `UNVERIFIED` even when
the bytes download successfully. For previously archived documents, retain
`historical_document_sha256` to detect changed bytes. BSE mappings also need
`identity_mapping` with instrument ID, BSE security code, archived path/digest,
reviewer and verified status. Retrieval time and URL dates cannot replace
exchange dissemination.

Every batch rebuilds coverage, ceiling and missing cells and records all five
productivity metrics per 100 queries, plus query/usable-filing counts by route.
An unattempted route has no measured productivity. A zero-query rate is null.
Returns never influence priority or route selection. Stop unproductive loops
and review missing official routes before spending more queries.

Use `quant.pipeline.report_historical_forward_phase` to measure the retained
filing/share/queue/ceiling/verification reports. Then refresh canonical JSON with
`quant.pipeline.write_current_status --data-dir data/historical-forward-validation`.
The status writer separates public main, research-certified SHA and whether the
certificate applies to the clean local implementation. Old evidence must retain
its own SHA and timestamp. Final clean-SHA certification is generated after
publication with `quant.pipeline.certify_implementation`; local test evidence
and live results remain separate.
