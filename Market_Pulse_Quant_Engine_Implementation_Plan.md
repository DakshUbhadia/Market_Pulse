# Market Pulse — Zero-Cost Quant Engine Implementation Plan

**Repository audited:** `https://github.com/DakshUbhadia/Market_Pulse`  
**Branch:** `main`  
**Audit date:** 2026-11-09  
**Objective:** Add a serious, evidence-driven Indian-equity quantitative recommendation engine to the existing Market Pulse application at approximately **₹0/month incremental cost**, for **single-user personal research**.

---

## 0. Executive decision

Do **not** rebuild Market Pulse.

Keep the existing:

- Next.js 16 application and UI
- TypeScript codebase
- Better Auth
- MongoDB/Mongoose application database
- Watchlists and alerts
- Simulator/paper-portfolio workflow
- Inngest email workflows
- Gemini explanation layer
- Existing Yahoo/Finnhub/TradingView features as convenience/UI features

Add a separate **local-first Python quantitative research pipeline** whose only production responsibility is to publish validated outputs into MongoDB for the existing Next.js application to display.

### Recommended zero-cost stack

```text
NSE public EOD/archive files + NSE corporate filings + RBI data
                    +
        Dhan free instrument-master CSV
                    |
                    v
             Python quant pipeline
       pandas / numpy / scipy / sklearn
                    |
             DuckDB + Parquet
        (local research/backtesting)
                    |
                    +-------> MongoDB Atlas
                               rolling live window
                               model runs
                               recommendations
                               outcomes
                                    |
                                    v
                              Existing Next.js
                                    |
                              Gemini explanation
```

### Most important design rule

The existing heuristic `Market Scope` and `Options` scanners must **not** become the source of the new quant recommendations.

The new quant path must be:

```text
point-in-time data
-> deterministic features
-> validated models
-> risk filters
-> ranked output
-> immutable recommendation record
-> UI
```

---

# 1. Repository audit — verified current state

The following findings are based on the actual `main` branch files, not only the README.

## 1.1 Core application stack

### `package.json`

Current relevant dependencies include:

- `next` 16.0.8
- React 19
- TypeScript
- `mongoose` / `mongodb`
- `better-auth`
- `inngest`
- `yahoo-finance2`
- `nodemailer`
- `lightweight-charts`

There is currently **no Python quant stack**, no backtesting library, no ML library, no analytical database, and no dedicated research/model service.

**Status:** reusable application shell; quant layer missing.

---

## 1.2 Navigation and product surfaces

### `src/lib/constants.ts`

Current navigation:

```text
/dashboard
/market-scope
/options
/simulator
/search
/watchlist
```

There is no dedicated Quant Research page.

### Required change

Add:

```text
/quant
```

Do not replace `Market Scope`. Keep the old scanner separate so users—or in this case you—can distinguish experimental intraday heuristics from validated quantitative research.

---

## 1.3 Current Indian security universe is BSE-centric

### `src/lib/constants.ts`

Verified behavior:

- `BSE_STOCKS` is the active curated Indian list.
- A large `NSE_STOCKS` list exists but is commented out.
- `getStocksForMarket('IN')` returns BSE names with `.BO` Yahoo suffixes.
- `toTradingViewSymbol()` explicitly says NSE is intentionally not supported and maps Indian names to BSE.

### `src/lib/actions/finnhub.actions.ts`

`toYahooTicker()` states:

```text
India is BSE-only in this app; coerce any NSE inputs to BSE.
```

### Why this must change

A quantitative Indian-equity engine should use **NSE as its primary research/trading universe**, while preserving BSE identifiers for mapping/fallback.

Do not use Yahoo ticker strings as canonical security IDs.

### New canonical identity

Use an internal immutable ID and map all external identifiers:

```text
instrument_id
isin
nse_symbol
bse_scrip_code
bse_symbol
dhan_security_id
yahoo_nse_symbol
yahoo_bse_symbol
```

ISIN should be a principal cross-source identity key where available.

---

## 1.4 Current quote pipeline is mostly Yahoo-driven

### `src/lib/actions/finnhub.actions.ts`

Despite the filename, realtime quote methods now use Yahoo Finance batching.

`getMultipleStockQuotesRealtime()` calls the Yahoo batch path and maintains fallback cache/backoff logic.

`getStockQuoteRealtime()` explicitly notes:

```text
Realtime watchlist data now comes from Yahoo Finance.
```

### `src/app/api/quotes/stream/route.ts`

Current SSE behavior:

- accepts up to 50 instruments per connection;
- polls quote backend around every 6 seconds;
- stores last-known good prices in process memory;
- permits stale fallback for roughly 2 minutes.

### Assessment

Good enough for your existing simulator/watchlist display.

Not appropriate as the data source for a research-grade EOD recommendation model.

### Plan

- Keep it for current UI/live display.
- Do **not** train or score the quant model from this feed.
- Quant engine uses official/free EOD history.

---

## 1.5 Current `Market Scope` logic is heuristic, not institutional flow

### `src/lib/actions/analysis.actions.ts`

Current `StockAnalysis` contains:

```text
rFactor
strongMoneySignal
strongMoneyScore
```

`rFactor` is simply position within the 52-week range:

```text
(current - 52wLow) / (52wHigh - 52wLow)
```

`computeStrongMoney()` combines Yahoo fields and rules such as:

- insider share activity;
- institutional holding percentage;
- 52-week-range position;
- volume spike;
- current price versus open.

### `src/lib/actions/momentum.actions.ts`

`analyzeInstitutionalFlow()` labels above-average bullish candles as institutional buying and bearish candles as institutional selling.

This is not observed institutional order flow.

### Required action

Before the quant engine is promoted, rename language such as:

```text
institutionalFlow
bigPlayersBuying
strongMoney
```

to descriptive names such as:

```text
volumePricePressure
highVolumeBullishPressure
heuristicFlowScore
```

unless a signal is genuinely computed from institutional ownership/trade data.

**Do not feed these heuristic labels into v1 of the quant engine.**

---

## 1.6 Current momentum radar is intraday/heuristic

### `src/components/analysis/MomentumRadarPanel.tsx`
### `src/lib/actions/momentum.actions.ts`

Current functionality includes:

- short-horizon momentum change;
- RSI;
- SMA context;
- relative volume;
- breakout confidence scores;
- browser/local-storage caching;
- high-confidence alert toasts.

`MomentumRadarPanel` can display alerts labelled 95%+ confidence.

### Recommendation

Treat current `confidenceScore` as a **heuristic score**, not a calibrated probability.

Do not call it a probability of success unless a proper historical calibration demonstrates that interpretation.

The new quant engine should use terms such as:

```text
Quant Score: 92nd percentile
```

rather than:

```text
92% probability of profit
```

until calibration exists.

---

## 1.7 Current Options page is not an option-chain quant engine

### `src/app/(root)/options/OptionsClient.tsx`

The page combines:

- `TomHougaardAlert`
- `OptionsRadarPanel`
- `OptionsScopePanel`

The underlying logic is mostly stock/index price and volume analysis. It does not currently maintain a complete historical options surface with IV, Greeks, OI and executable bid/ask data.

### Action

Leave this feature untouched for the first quant-engine milestone.

Options research is Phase 6, not a dependency for a long-only Indian equity recommendation system.

---

## 1.8 Tom Hougaard rule should remain experimental

### `src/components/analysis/TomHougaardAlert.tsx`
### `src/lib/actions/tom-hougaard.actions.ts`

The UI contains historical accuracy comments, while the action fetches recent Yahoo candles and evaluates two calendar rules on Nifty/Bank Nifty/Sensex or US indices.

### Action

Keep it as an experimental rule scanner, but:

- do not mix it with quant recommendation score;
- do not use its claimed historical accuracy in the new Quant UI unless the exact backtest is reproducible in the new backtest framework.

---

## 1.9 MongoDB models are reusable

### `src/database/mongoose.ts`

A cached Mongoose connection is already implemented.

### Existing useful models

- `src/database/models/watchlist.model.ts`
- `src/database/models/alert.model.ts`
- `src/database/models/portfolio.model.ts`
- `src/database/models/transaction.model.ts`
- `src/database/models/user.model.ts`
- `src/database/models/email-preferences.model.ts`

### Reuse

Use MongoDB for:

- published recommendations;
- latest feature snapshot;
- model-run metadata;
- recommendation outcome tracking;
- rolling ~400-day live price window if GitHub Actions is used;
- watchlist integration.

### Do not use MongoDB as the 15-year research warehouse

A free MongoDB tier can be conserved by keeping the large historical research corpus locally in compressed Parquet files queried with DuckDB.

---

## 1.10 Simulator is a strong forward-testing foundation

### `src/lib/actions/trading.actions.ts`
### `src/app/(root)/simulator/SimulatorDashboard.tsx`

The application already supports:

- Indian/US virtual balances;
- positions;
- transactions;
- live quote updates;
- portfolio current value.

### Important defect

`SimulatorDashboard.tsx` calculates some "today P/L" and daily history as:

```text
sells - buys
```

which is cash flow, not true P&L.

### Required fix before quant forward testing

Implement:

```text
realized_pnl
unrealized_pnl
fees
benchmark_return
portfolio_nav
```

The repaired simulator can become the forward/paper-validation layer for the quant model.

---

## 1.11 Watchlist and alerts are reusable

### `src/components/watchlist/WatchlistPageClient.tsx`
### `src/lib/actions/alerts.actions.ts`

Existing alerts support:

- price;
- percentage;
- P/E;
- greater/less/crossing conditions;
- frequency controls;
- email delivery.

### Extension later

Add alert types:

```text
QUANT_SCORE
QUANT_RANK
RISK_LEVEL
MODEL_STATE
```

Example:

```text
Notify when ICICIBANK quant percentile crosses above 90.
```

---

## 1.12 Inngest is reusable but should not calculate alpha

### `src/lib/inngest/functions.ts`
### `src/app/api/inngest/route.ts`

Current Inngest functions include:

- signup email;
- daily news summary;
- daily trading insights.

The daily insights currently call `getStrongMoneyScope()` and then use Gemini/email generation.

### New responsibility

Inngest should eventually read a completed quant recommendation record and explain/notify it.

It should **not** independently determine which stocks to recommend.

---

## 1.13 TypeScript build errors are currently ignored

### `next.config.ts`

Current setting:

```ts
typescript: {
  ignoreBuildErrors: true,
}
```

This is risky when introducing a quantitative recommendation API and strongly typed score schemas.

### Plan

Do not change this on day one if existing code depends on it, but create a roadmap task to:

1. run `npx tsc --noEmit`;
2. fix existing type errors;
3. remove `ignoreBuildErrors`.

---

## 1.14 Tests are effectively missing as a product gate

`package.json` has no meaningful `test` script for the quant logic.

### Quant engine requirement

Python side must include:

```text
pytest
```

and TypeScript integration should get at least API/schema tests.

---

# 2. Scope of the zero-cost Quant Engine v1

Do not attempt to build the final institutional platform immediately.

The first production-quality research model should answer one question:

> Among sufficiently liquid NSE equities, which stocks have the strongest combination of medium-term momentum, relative strength, liquidity and controlled downside risk for approximately the next 1–3 months?

This model is selected because:

- the required data are available free;
- it is historically testable over 10–15+ years;
- it does not require realtime data;
- it does not require expensive analyst-estimate history;
- it aligns with the research already performed;
- it is appropriate for a single-user daily investment workflow.

### v1 horizon

Primary target:

```text
63 trading days
```

Also calculate diagnostics for:

```text
21 days
126 days
```

but do not call them production recommendation horizons until independently validated.

---

# 3. Free data strategy

## 3.1 Important Dhan correction

Dhan's **instrument-master CSV is publicly accessible/free**.

Dhan's current **Data API subscription is not free**; Dhan states that realtime market data, historical data, option chains and market depth are part of a ₹499 + GST/month Data API subscription.

Therefore the zero-cost implementation will:

### Use Dhan for

- instrument master;
- Security ID mapping;
- NSE/BSE/MCX identity metadata;
- optional trading integration later through free Trading API.

### Not require Dhan for

- daily historical prices;
- live prices;
- model inference.

If you later decide ₹499/month is acceptable, Dhan Data API can be plugged in without changing the model architecture.

---

# 4. Data-source matrix — ₹0 version

| Data | Free source | Frequency | Needed for v1? | Local module |
|---|---|---:|---:|---|
| Instrument/security IDs | Dhan instrument CSV + NSE security file | daily | Yes | `quant/data/dhan_instruments.py` |
| NSE OHLCV | NSE bhavcopy archives | daily | **Yes** | `quant/data/nse_bhavcopy.py` |
| Traded value | NSE bhavcopy/full bhavdata | daily | **Yes** | same |
| Delivery quantity/% | NSE full bhavdata / delivery file | daily | Recommended | `nse_delivery.py` |
| Security series/status | NSE security file/bhavcopy | daily | **Yes** | `nse_security_master.py` |
| Corporate actions | NSE corporate filings | event | **Yes** | `nse_corporate_actions.py` |
| Nifty/index history | NSE historical index data | daily | **Yes** | `nse_indices.py` |
| Current Nifty 500 + industry | NSE Indices | monthly | Recommended | `nifty_constituents.py` |
| India VIX | NSE index reports | daily | Recommended | `nse_vix.py` |
| FII/DII flows | NSE report | daily | Optional v1 | `nse_flows.py` |
| Financial results | NSE financial-result/XBRL filings | quarterly/event | Phase 2 | `nse_fundamentals.py` |
| Shareholding | NSE shareholding/XBRL | quarterly | Phase 2 | `nse_shareholding.py` |
| Corporate announcements | NSE filings | event | Phase 3 | `nse_announcements.py` |
| Repo/risk-free/rates | RBI DBIE | daily/event | Recommended | `rbi.py` |
| Current live UI quotes | existing Yahoo implementation | seconds | UI only | keep existing TS |
| Analyst estimates/revisions | no robust free PIT source | event | **Skip initially** | later paid/optional |
| Intraday tick/order book | not needed | realtime | No | skip |
| Option chain/IV/OI | Dhan paid / NSE derivative data | realtime/EOD | No | Phase 6 |

---

# 5. NSE price-history implementation

## 5.1 Two bhavcopy eras

The cash-market file format changed on **8 July 2024**.

Build two parsers.

### Legacy historical path

For dates before 2024-07-08:

```text
https://nsearchives.nseindia.com/content/historical/EQUITIES/{YYYY}/{MON}/cm{DD}{MON}{YYYY}bhav.csv.zip
```

Example pattern:

```text
.../EQUITIES/2020/JAN/cm02JAN2020bhav.csv.zip
```

### Current UDiFF path

For 2024-07-08 onward:

```text
https://nsearchives.nseindia.com/content/cm/BhavCopy_NSE_CM_0_0_0_{YYYYMMDD}_F_0000.csv.zip
```

### Parser contract

Normalize both formats into:

```text
trade_date
symbol
series
open
high
low
close
last
previous_close
volume
traded_value
num_trades       # when available
source_file
source_hash
```

The model must never care which bhavcopy format produced the row.

---

# 6. Data dictionary — v1

## 6.1 Instrument fields

```text
instrument_id             internal UUID/hash
isin                      ISIN
nse_symbol                canonical NSE symbol
company_name
series                     EQ/BE/etc.
listing_date               when obtainable
active
sector                     current sector
industry                   current industry
dhan_security_id
bse_scrip_code             optional
```

### Essential live eligibility

Use only ordinary equity series intended for normal trading, initially `EQ`.

---

## 6.2 Daily market fields

```text
trade_date
instrument_id
open
high
low
close
previous_close
volume
traded_value
num_trades
deliverable_qty            optional v1
deliverable_pct            optional v1
```

Minimum historical depth:

```text
2010-present
```

Preferred if practical:

```text
2005-present
```

---

## 6.3 Corporate-action fields

```text
action_id
instrument_id
action_type
announcement_date
ex_date
record_date
ratio_numerator
ratio_denominator
cash_amount
purpose_raw
source
```

Action types:

```text
SPLIT
BONUS
DIVIDEND
RIGHTS
MERGER
DEMERGER
SYMBOL_CHANGE
OTHER
```

Do not use adjusted prices until adjustment logic has tests for splits and bonuses.

---

# 7. Free fundamental-data plan

Fundamentals are valuable, but they are the hardest part to reconstruct point-in-time for free.

NSE provides public financial-result and Integrated Filing pages with XBRL and **broadcast timestamps**. Shareholding filings similarly provide submission/revision/broadcast timestamps.

## Critical rule

Never use:

```text
period_end
```

as the date a model could know the result.

Use:

```text
broadcast_at / exchange_received_at
```

## Phase-2 fundamental fields

### Industrial/non-financial companies

```text
revenue
operating_profit / EBITDA
PAT
EPS
assets
equity
total_debt
cash
interest_expense
CFO
capex
```

Derived:

```text
revenue_growth_yoy
EPS_growth_yoy
operating_margin
ROE
ROIC
debt_to_equity
interest_coverage
FCF
FCF_yield
PE
PB
EV_EBITDA
```

### Banks/NBFCs

Use a separate schema/model:

```text
deposits
advances
NIM
GNPA
NNPA
ROA
ROE
CET1
capital_adequacy
credit_cost
```

Do not apply industrial-company EV/EBITDA logic to banks.

## Honest limitation

A **fully clean 10–15 year point-in-time fundamental backtest is the hardest zero-cost component**.

Therefore:

1. ship and validate the price/risk/liquidity model first;
2. build the NSE XBRL archive forward immediately;
3. backfill historical filings as coverage permits;
4. do not mix current fundamentals into historical dates where release timing is unknown.

If historical fundamental coverage fails a quality threshold, keep those factors out of the historical model rather than fabricate a result.

---

# 8. Storage architecture for ₹0

## 8.1 Local research store: Parquet + DuckDB

Add:

```text
data/
├── raw/
│   ├── nse/
│   ├── nifty/
│   ├── rbi/
│   └── dhan/
├── normalized/
│   ├── prices/
│   ├── corporate_actions/
│   ├── indices/
│   └── fundamentals/
├── features/
└── models/
```

All of `data/` should be gitignored.

### Why DuckDB

DuckDB can query compressed Parquet files directly and costs nothing.

It is ideal for:

- 15 years of daily cross-sectional data;
- rolling windows;
- joins;
- backtests;
- local research.

You do not need TimescaleDB, Redis, ClickHouse or a cloud warehouse for one user.

---

## 8.2 MongoDB production/live store

Keep Mongo for small application-facing datasets.

Add collections/models for:

```text
quant_instruments
quant_price_windows
quant_feature_latest
quant_model_runs
quant_recommendations
quant_recommendation_outcomes
```

### `quant_price_windows`

One document per instrument, only rolling history needed for live inference:

```json
{
  "instrumentId": "...",
  "symbol": "ICICIBANK",
  "bars": [
    {
      "d": "2026-11-09",
      "o": 0,
      "h": 0,
      "l": 0,
      "c": 0,
      "v": 0,
      "tv": 0
    }
  ],
  "updatedAt": "..."
}
```

Keep about:

```text
400-450 trading days
```

per live instrument.

This is enough for 12-month momentum plus safety buffers.

### Why not upload 15 years to Mongo

The local backtest corpus does not need to be served by the website. Keeping it in Parquet saves free-tier storage.

---

# 9. New Python project structure

Add this to the repository:

```text
quant/
├── README.md
├── requirements.txt
├── config.py
│
├── data/
│   ├── __init__.py
│   ├── http.py
│   ├── dhan_instruments.py
│   ├── nse_bhavcopy.py
│   ├── nse_security_master.py
│   ├── nse_indices.py
│   ├── nse_corporate_actions.py
│   ├── nse_fundamentals.py
│   ├── nse_shareholding.py
│   ├── nse_flows.py
│   └── rbi.py
│
├── storage/
│   ├── duckdb_store.py
│   ├── parquet_store.py
│   └── mongo_store.py
│
├── quality/
│   ├── schemas.py
│   ├── validators.py
│   └── freshness.py
│
├── features/
│   ├── normalize.py
│   ├── momentum.py
│   ├── relative_strength.py
│   ├── risk.py
│   ├── liquidity.py
│   ├── volume.py
│   ├── fundamentals.py
│   └── regime.py
│
├── models/
│   ├── factor_v1.py
│   ├── elastic_net_v2.py
│   └── registry.py
│
├── portfolio/
│   ├── risk.py
│   └── construction.py
│
├── backtest/
│   ├── engine.py
│   ├── universe.py
│   ├── costs.py
│   ├── metrics.py
│   ├── walk_forward.py
│   └── bootstrap.py
│
├── pipeline/
│   ├── bootstrap_history.py
│   ├── update_eod.py
│   ├── build_features.py
│   ├── run_inference.py
│   ├── publish.py
│   └── update_outcomes.py
│
└── tests/
    ├── test_bhavcopy.py
    ├── test_adjustments.py
    ├── test_features.py
    ├── test_no_lookahead.py
    ├── test_costs.py
    └── test_model.py
```

---

# 10. Python dependencies

`quant/requirements.txt`:

```text
pandas
numpy
scipy
scikit-learn
statsmodels
duckdb
pyarrow
pymongo
requests
beautifulsoup4
lxml
pydantic
pytest
joblib
```

Optional later:

```text
xgboost
lightgbm
cvxpy
```

Do not install them until the baseline needs them.

---

# 11. `.gitignore` changes

Current `.gitignore` does not exclude a research data directory.

Add:

```gitignore
# Quant research data
/data/
/quant/.venv/
/quant/.pytest_cache/
/quant/__pycache__/
**/__pycache__/
*.pyc
*.duckdb
*.parquet

# Local trained artifacts if large
/quant/artifacts/local/
```

Small versioned model metadata may remain committed separately under something such as:

```text
quant/model_specs/
```

---

# 12. Data download reliability

NSE pages may require normal browser-like sessions and can reject aggressive automated requests.

Implement `quant/data/http.py` with:

```text
requests.Session
browser User-Agent
retry with exponential backoff
rate limiting
local file cache
checksum
request timeout
```

Rules:

- never redownload a raw file already stored with a valid checksum;
- sleep between requests;
- retry 429/5xx conservatively;
- fail the pipeline rather than substitute invented/mock data;
- retain source filename and SHA-256.

For daily production, only one or a few files should be needed, so load is negligible.

---

# 13. Universe construction

Do not backtest on today's Nifty 500 constituents.

That causes survivorship bias.

For v1, construct the historical eligible universe from securities that actually appear in each day's NSE cash bhavcopy.

## Initial eligibility rules

```text
series == EQ
history >= 252 trading days
close >= ₹20 or ₹50  [test both]
median traded value 60d >= ₹5 crore
trading-day availability >= 95%
not under unresolved data-quality flag
```

Then optionally restrict to the top 300-500 by median traded value.

The thresholds must be tested for robustness; do not optimize to one magical number.

---

# 14. v1 feature engineering

## 14.1 Price momentum

```text
mom_1m   = close_t / close_t-21  - 1
mom_3m   = close_t / close_t-63  - 1
mom_6_1  = close_t-21 / close_t-126 - 1
mom_12_1 = close_t-21 / close_t-252 - 1
```

The skip-month variants reduce sensitivity to very short-term reversal.

---

## 14.2 Relative strength

```text
vs_nifty_3m = stock_63d_return - Nifty500_63d_return
vs_nifty_6m = stock_126d_return - Nifty500_126d_return
```

When sector mapping is available:

```text
vs_sector_3m
vs_sector_6m
```

---

## 14.3 Distance to 52-week high

```text
distance_52w_high = close / rolling_max_252(close) - 1
```

Unlike the current `R-Factor`, this should be only one input among many rather than the core score.

---

## 14.4 Volatility

```text
vol_20d  = std(daily_returns, 20)  * sqrt(252)
vol_63d  = std(daily_returns, 63)  * sqrt(252)
vol_252d = std(daily_returns, 252) * sqrt(252)
```

---

## 14.5 Downside volatility

```text
downside_vol_63d = std(negative_daily_returns, 63) * sqrt(252)
```

---

## 14.6 Beta

```text
beta_252d = cov(stock_return, Nifty500_return) / var(Nifty500_return)
```

Use aligned trading days only.

---

## 14.7 Drawdown

```text
rolling_peak = cumulative maximum
current_drawdown = close / rolling_peak - 1
max_dd_252d = minimum drawdown over 252 sessions
```

---

## 14.8 Liquidity

```text
adv_20d = median(traded_value, 20)
adv_60d = median(traded_value, 60)
```

Amihud-style illiquidity:

```text
amihud_60d = mean(abs(return) / traded_value)
```

---

## 14.9 Volume confirmation

```text
relative_volume_20d = volume_today / median(volume, 20)
```

Do not label this institutional flow.

---

# 15. Robust cross-sectional normalization

For each feature and date:

1. clip/winsorize extreme observations;
2. normalize cross-sectionally;
3. sector-neutralize when sector data are reliable.

Prefer median/MAD robust z-score:

```text
z = (x - median(x)) / (1.4826 * MAD(x))
```

Clip final z-scores initially to approximately:

```text
[-3, +3]
```

This prevents one bad vendor/source value from dominating a recommendation.

---

# 16. v1 deterministic factor model

Start with a simple score that can be completely explained.

Example research specification:

```text
Momentum block        40%
Relative strength     15%
Low/downside risk     20%
Liquidity             10%
Volume confirmation    5%
Market regime         10%
```

Example:

```text
momentum = mean(
    z(mom_3m),
    z(mom_6_1),
    z(mom_12_1)
)

risk_quality = -mean(
    z(vol_63d),
    z(downside_vol_63d),
    z(max_drawdown_252d)
)

liquidity_quality = mean(
    z(log(adv_60d)),
    -z(log(amihud_60d))
)
```

Then:

```text
raw_score =
    0.40 * momentum
  + 0.15 * relative_strength
  + 0.20 * risk_quality
  + 0.10 * liquidity_quality
  + 0.05 * volume_quality
  + 0.10 * regime_fit
```

Convert to cross-sectional percentile:

```text
quant_score = percentile_rank(raw_score) * 100
```

### UI interpretation

Correct:

```text
Quant Score 92/100
92nd percentile among 327 eligible stocks
```

Incorrect:

```text
92% probability of making money
```

---

# 17. Market-regime layer

Keep v1 simple.

Inputs:

```text
Nifty 500 above/below 200DMA
Nifty 50/500 50DMA slope
market breadth
India VIX percentile
optional FII/DII 20-day cumulative flow
```

Classify:

```text
RISK_ON
NEUTRAL
RISK_OFF
```

Use regime primarily to change risk/exposure and minimum score threshold, not to completely invert stock rankings.

---

# 18. v2: Elastic Net model

Only after v1 is fully backtested.

## Target

For date `t` and stock `i`:

```text
y(i,t) = stock return over next 63 trading days
       - benchmark/sector return over next 63 trading days
```

Optional risk-adjusted target:

```text
y* = residual_63d_return / current_volatility
```

## Model

Elastic Net:

```text
minimize
sum((y - Xβ)^2)
+ λ1 * ||β||1
+ λ2 * ||β||2^2
```

Why:

- financial features are correlated;
- regularization limits unstable coefficients;
- interpretable;
- low compute;
- easy to validate.

Do not add XGBoost/LightGBM until Elastic Net beats the deterministic baseline out of sample.

---

# 19. Fundamental factor integration — Phase 2

When point-in-time data coverage is acceptable, add:

```text
quality_score
growth_score
value_score
```

Suggested live composite later:

```text
25% momentum
20% earnings/growth
20% quality
15% valuation
15% downside risk
 5% liquidity/regime
```

These weights are only a starting hypothesis.

Use historical information coefficients or regularized regression to estimate weights.

Do not tune them manually until the backtest looks attractive.

---

# 20. Backtesting engine requirements

The backtester is mandatory before displaying recommendations as validated.

## 20.1 Point-in-time universe

On historical date `t`, use only stocks trading on `t` and data known by `t`.

## 20.2 No same-close execution

If the model uses the close at `t`, the backtest cannot buy at that same close.

Use:

```text
next trading day open
```

or a conservative next-day execution approximation.

## 20.3 Holding horizon

Initial research:

```text
42 trading days
63 trading days
84 trading days
```

The user-facing model should use whichever broad region is robust, not the single best exact day.

## 20.4 Portfolio

Initial implementation:

```text
top 20-30 stocks
equal weight or inverse volatility
max position 5%
sector cap 25%
monthly rebalance
entry buffer: top 10-15%
exit buffer: falls below top 30-40%
```

The entry/exit buffer reduces turnover.

---

# 21. Indian transaction-cost model

Even for a free software implementation, the backtest must not assume free trading.

Create `quant/backtest/costs.py`.

At minimum model:

```text
STT
brokerage if applicable
exchange transaction charge
SEBI charge
GST on applicable service charges
stamp duty
bid/ask spread
slippage
```

For the first sanity check, use a deliberately conservative aggregate delivery-equity round-trip cost assumption in addition to the detailed cost function.

Then stress:

```text
1.0x cost
1.5x cost
2.0x cost
```

If the strategy dies at 1.5x plausible costs, do not deploy it.

---

# 22. Walk-forward validation

Do not randomly split financial time series.

Suggested structure:

```text
Train: 2010-2015   Validate: 2016   Test: 2017
Train: 2011-2016   Validate: 2017   Test: 2018
...
Train: 2018-2023   Validate: 2024   Test: 2025
Train: 2019-2024   Validate: 2025   Test: 2026
```

For overlapping 63-day labels, implement purge/embargo around validation/test windows.

---

# 23. Metrics that determine whether the engine is useful

Prediction metrics:

```text
Spearman information coefficient (IC)
IC mean
IC information ratio
rank monotonicity by decile
```

Portfolio metrics:

```text
CAGR
annualized volatility
Sharpe
Sortino
maximum drawdown
Calmar
CVaR
information ratio vs Nifty 500
beta
turnover
hit rate
rolling 1y/3y excess return
```

Operational metrics:

```text
missing-data rate
stale-data rate
pipeline failure rate
universe size
excluded instruments
source freshness
```

---

# 24. Go-live research gates

Do not publish the model as a serious recommendation engine until it passes these checks.

Suggested minimum research standards:

```text
[ ] 10-15+ year historical period
[ ] survivorship-aware universe
[ ] no same-close lookahead
[ ] transaction costs included
[ ] positive out-of-sample IC
[ ] top-decile returns broadly monotonic
[ ] net information ratio approximately > 0.5 preferred
[ ] no single year/sector explains most alpha
[ ] remains positive under 1.5x cost stress
[ ] parameter neighborhoods work
[ ] live paper-forward period completed
```

These are hurdles, not promises of future returns.

---

# 25. MongoDB models to add

## `src/database/models/quant-instrument.model.ts`

```ts
{
  instrumentId: string,
  isin?: string,
  nseSymbol: string,
  companyName: string,
  series: string,
  sector?: string,
  industry?: string,
  dhanSecurityId?: string,
  active: boolean,
  updatedAt: Date
}
```

---

## `src/database/models/quant-model-run.model.ts`

```ts
{
  runId: string,
  modelName: string,
  modelVersion: string,
  featureVersion: string,
  asOfDate: Date,
  generatedAt: Date,
  status: "SUCCESS" | "FAILED" | "DEGRADED",
  universeSize: number,
  dataQuality: object,
  gitCommit?: string,
  metrics?: object
}
```

---

## `src/database/models/quant-recommendation.model.ts`

```ts
{
  runId: string,
  instrumentId: string,
  symbol: string,
  companyName: string,
  asOfDate: Date,
  price: number,
  priceTimestamp: Date,
  horizon: "63D",
  quantScore: number,
  rank: number,
  universeSize: number,
  factors: {
    momentum: number,
    relativeStrength: number,
    risk: number,
    liquidity: number,
    volume: number,
    quality?: number,
    value?: number,
    growth?: number
  },
  risk: {
    volatility63d: number,
    volatility252d: number,
    beta252d: number,
    maxDrawdown252d: number,
    downsideVol63d: number
  },
  dataStatus: "CURRENT" | "STALE" | "INCOMPLETE",
  state: "RESEARCH" | "CANDIDATE" | "ACTIVE" | "DOWNGRADED" | "EXITED",
  reasons: string[],
  riskFlags: string[],
  modelVersion: string,
  createdAt: Date
}
```

---

## `src/database/models/quant-outcome.model.ts`

Track what actually happened after every recommendation.

```ts
{
  recommendationId: ObjectId,
  horizonDays: number,
  measuredAt: Date,
  stockReturn: number,
  benchmarkReturn: number,
  excessReturn: number,
  maxAdverseExcursion: number,
  maxFavorableExcursion: number
}
```

This prevents the system from remembering only its winners.

---

# 26. Next.js integration

## 26.1 Modify `src/lib/constants.ts`

Add:

```ts
{ href: "/quant", label: "Quant Research" }
```

Do **not** make the new page rely on the large hard-coded `BSE_STOCKS` list.

Quant page reads its universe/results from Mongo.

---

## 26.2 Add server action

Create:

```text
src/lib/actions/quant.actions.ts
```

Functions:

```text
getLatestQuantRun()
getQuantRecommendations(horizon, limit)
getQuantRecommendation(symbol)
getQuantHistory(symbol)
getQuantModelHealth()
```

All methods must return data freshness and model version.

---

## 26.3 Add pages

```text
src/app/(root)/quant/page.tsx
src/app/(root)/quant/QuantResearchClient.tsx
src/app/(root)/quant/[symbol]/page.tsx
```

---

## 26.4 Add components

```text
src/components/quant/QuantStatusBanner.tsx
src/components/quant/QuantRankingTable.tsx
src/components/quant/QuantScoreCard.tsx
src/components/quant/FactorBreakdown.tsx
src/components/quant/RiskMetrics.tsx
src/components/quant/RecommendationHistory.tsx
src/components/quant/DataFreshnessBadge.tsx
src/components/quant/ModelInfo.tsx
```

---

# 27. Quant page UI specification

Header:

```text
Quant Research — India
Data as of: 09 Nov 2026
Model: factor_63d_v1
Status: CURRENT
Universe: 327 eligible NSE equities
```

Table:

```text
Rank
Symbol
Company
Quant Score
Momentum
Relative Strength
Risk
Liquidity
Price
1M Return
3M Return
Volatility
Data Status
```

Filters:

```text
minimum score
sector
risk level
minimum liquidity
watchlist only
```

Do not display an expected-return percentage until the model has enough walk-forward observations to calibrate empirical outcome ranges.

---

# 28. Individual stock Quant page

Show:

### Score

```text
Quant Score: 91.4 / 100
Rank: 18 / 327
```

### Factors

```text
Momentum             +1.35 z
Relative strength    +0.91 z
Risk quality         +0.62 z
Liquidity            +1.72 z
Volume confirmation  +0.20 z
```

### Risk

```text
63d annualized volatility
252d annualized volatility
beta
252d maximum drawdown
current drawdown
ADV
```

### Model information

```text
Model version
Feature version
Data timestamp
Recommendation creation timestamp
Status
```

### Explanation

Gemini can explain these already-calculated values.

It must never invent a number.

---

# 29. Gemini integration rule

Correct:

```text
Quant engine JSON
-> Gemini explanatory prompt
-> natural-language explanation
```

Incorrect:

```text
Gemini
-> choose stocks
-> invent score
```

Create a strict prompt/schema where Gemini receives fields such as:

```json
{
  "score": 91.4,
  "rank": 18,
  "universeSize": 327,
  "factorContributions": {},
  "riskMetrics": {},
  "riskFlags": []
}
```

Gemini may only return:

```json
{
  "summary": "...",
  "drivers": ["..."],
  "risks": ["..."],
  "monitor": ["..."]
}
```

The server should reject Gemini output containing unsupported new numeric forecasts.

---

# 30. Inngest integration

Keep current Inngest infrastructure.

### Do not use Inngest for heavy historical backtesting

Run that locally.

### Modify later

`src/lib/inngest/functions.ts`

Current daily trading insights depend on `getStrongMoneyScope()`.

Replace the recommendation section with:

```text
get latest validated quant recommendations
-> pass deterministic output to Gemini
-> email explanation
```

Keep news summary as a separate feature.

---

# 31. Daily zero-cost automation

## Option A — recommended during development: local scheduled task

Run on your computer after market close:

```bash
python -m quant.pipeline.update_eod
python -m quant.pipeline.build_features
python -m quant.pipeline.run_inference
python -m quant.pipeline.publish
```

Use Windows Task Scheduler / cron.

Advantages:

- easiest debugging;
- local Parquet history available;
- no cloud state problem;
- ₹0.

---

## Option B — later: GitHub Actions scheduled daily pipeline

Because the repository is public, a lightweight scheduled workflow can run the daily EOD update.

Add:

```text
.github/workflows/quant-eod.yml
```

Concept:

```yaml
name: Quant EOD Pipeline

on:
  workflow_dispatch:
  schedule:
    - cron: "30 12 * * 1-5"  # ~18:00 IST

jobs:
  run-quant:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install -r quant/requirements.txt
      - run: python -m quant.pipeline.update_eod
      - run: python -m quant.pipeline.build_features
      - run: python -m quant.pipeline.run_inference
      - run: python -m quant.pipeline.publish
        env:
          MONGODB_URI: ${{ secrets.MONGODB_URI }}
```

### State design for GitHub Actions

GitHub runners are ephemeral.

Therefore daily cloud inference should retrieve its rolling 400-day bars from Mongo, append today's NSE file, recompute features, and write them back.

The full 15-year local Parquet research corpus remains local and is **not** required on the daily runner.

---

# 32. Live price versus live recommendation

These are different concepts.

### Live price

Your current SSE/Yahoo pipeline can continue updating the UI every few seconds.

### Quant recommendation

For a 1–3 month model, recompute:

```text
once per trading day after EOD data are validated
```

There is no useful reason to retrain/re-rank every six seconds.

A stock can show a current Yahoo price next to a recommendation whose evidence timestamp is yesterday's validated close, as long as the UI says so explicitly.

Example:

```text
Recommendation data: 09 Nov 2026 EOD
Live display price: 10 Nov 2026 10:21:06 IST
```

---

# 33. Freshness and failure rules

Never silently display stale output as current.

Implement states:

```text
CURRENT
STALE
INCOMPLETE
FAILED
```

Examples:

```text
if latest trading-day bhavcopy missing:
    do not publish new recommendation run

if < 95% expected universe has valid bars:
    mark run FAILED

if corporate-action adjustment unresolved:
    exclude that security

if model computation fails:
    leave prior run visible but mark STALE
```

---

# 34. Repair simulator for model forward testing

Modify:

```text
src/app/(root)/simulator/SimulatorDashboard.tsx
src/lib/actions/trading.actions.ts
src/database/models/transaction.model.ts
```

Add transaction fields if useful:

```text
fees
realizedPnl
strategyTag
recommendationId
modelVersion
```

Add paper strategies:

```text
Manual
Quant 63D v1
Factor Baseline
Nifty 500 benchmark
```

Then create a shadow portfolio from every model run.

This is much more useful than adding another visual indicator.

---

# 35. Current components that should remain separate

Do not delete these initially:

```text
MarketScopePanel
MomentumRadarPanel
OptionsRadarPanel
OptionsScopePanel
TomHougaardAlert
```

Instead label them clearly as:

```text
Intraday / Experimental Scanners
```

and keep the new `/quant` page as:

```text
Validated EOD Quant Research
```

This keeps backward compatibility while preventing mixed evidentiary standards.

---

# 36. Rename misleading terms

Priority refactor after v1 is functional:

### `src/lib/actions/momentum.actions.ts`

```text
analyzeInstitutionalFlow
```

->

```text
analyzeVolumePricePressure
```

### `src/lib/actions/analysis.actions.ts`

Prefer:

```text
heuristicFlowScore
volumeMomentumSignal
```

instead of `strongMoney` unless actual institutional data are used.

### UI copy

Replace wording such as:

```text
institutional buying
big players buying
```

with:

```text
high-volume bullish pressure
volume-supported price strength
```

when that is what the algorithm actually measured.

---

# 37. Detailed implementation phases

## Phase 0 — safety/refactor preparation

### Tasks

```text
[ ] create feature branch: quant-engine-v1
[ ] add /quant to navigation only after API is ready
[ ] add Python folder
[ ] add data/ to .gitignore
[ ] add pytest
[ ] document zero-cost data sources
[ ] add model terminology policy
```

### Do not yet

```text
[ ] change current Market Scope behavior
[ ] remove Yahoo
[ ] add ML
[ ] add options data
```

---

## Phase 1 — historical price foundation

### Files

```text
quant/data/nse_bhavcopy.py
quant/data/dhan_instruments.py
quant/storage/parquet_store.py
quant/storage/duckdb_store.py
quant/pipeline/bootstrap_history.py
quant/tests/test_bhavcopy.py
```

### Tasks

1. Download Dhan detailed instrument CSV.
2. Build instrument map.
3. Backfill NSE daily bhavcopies from 2010.
4. Handle legacy and UDiFF formats.
5. Normalize fields.
6. Save yearly/monthly Parquet partitions.
7. Query with DuckDB.
8. Validate random dates against official NSE files.

### Acceptance criteria

```text
>= 99.5% expected historical trading dates loaded
no duplicate symbol/date keys
numeric fields valid
legacy/current schema normalized identically
source URL + checksum retained
```

---

## Phase 2 — corporate actions + clean returns

### Files

```text
quant/data/nse_corporate_actions.py
quant/features/adjustments.py
quant/tests/test_adjustments.py
```

### Tasks

- download split/bonus/dividend events;
- build adjustment factors;
- verify split/bonus dates manually on sample companies;
- derive adjusted return series.

### Acceptance criterion

A known 1:2 split must not create an artificial -50% momentum signal.

---

## Phase 3 — v1 features and screener

### Files

```text
quant/features/momentum.py
quant/features/relative_strength.py
quant/features/risk.py
quant/features/liquidity.py
quant/features/normalize.py
quant/models/factor_v1.py
quant/pipeline/build_features.py
```

### Output

Local table:

```text
as_of
symbol
eligible
quant_score
rank
momentum_z
relative_strength_z
risk_z
liquidity_z
```

Do not publish yet.

---

## Phase 4 — backtester

### Files

```text
quant/backtest/engine.py
quant/backtest/costs.py
quant/backtest/metrics.py
quant/backtest/walk_forward.py
quant/tests/test_no_lookahead.py
```

### Compare

```text
v1 quant portfolio
Nifty 50
Nifty 500
simple 12-1 momentum
simple equal-weight liquid universe
```

### Kill criteria

If the complex score does not beat simple momentum/risk baselines out of sample, simplify it.

---

## Phase 5 — publish to Market Pulse

### Python

```text
quant/storage/mongo_store.py
quant/pipeline/publish.py
quant/pipeline/update_outcomes.py
```

### TypeScript

```text
src/database/models/quant-instrument.model.ts
src/database/models/quant-model-run.model.ts
src/database/models/quant-recommendation.model.ts
src/database/models/quant-outcome.model.ts
src/lib/actions/quant.actions.ts
```

### UI

```text
src/app/(root)/quant/page.tsx
src/app/(root)/quant/QuantResearchClient.tsx
src/app/(root)/quant/[symbol]/page.tsx
src/components/quant/*
```

---

## Phase 6 — forward testing

Use repaired simulator.

Run the model daily and create a shadow portfolio.

Do not change model parameters based on every short-term loss.

Track:

```text
model-run date
entry rank
entry score
entry next-session price
63d outcome
benchmark outcome
maximum adverse excursion
```

---

## Phase 7 — fundamentals

### Data

```text
NSE financial results
Integrated Filing XBRL
shareholding patterns
```

### Features

```text
quality
growth
value
ownership risk
promoter pledge
```

### Rule

A fundamental feature can enter production only after:

```text
point-in-time timestamps are reliable
historical coverage is quantified
missing-value behavior is tested
OOS result adds value
```

---

## Phase 8 — Elastic Net

Add only after deterministic v1 is stable.

Train locally.

Store model metadata:

```text
training_end_date
feature list
coefficients
scaler stats
hyperparameters
walk-forward metrics
Git commit
```

The daily runner performs inference only.

---

## Phase 9 — optional advanced work

Only after measured value:

```text
LightGBM/XGBoost
NLP/news
analyst estimates if a future free/paid source becomes available
portfolio optimization
stat-arb
options/OI/IV
Dhan paid realtime data
```

---

# 38. First concrete coding milestone

## Goal

Produce a local command that outputs the latest ranked 63-day research candidates using only free NSE EOD data.

### Definition of done

Running:

```bash
python -m quant.pipeline.bootstrap_history --from 2018-01-01
python -m quant.pipeline.build_features --as-of latest
python -m quant.pipeline.run_inference --model factor_v1
```

must produce something like:

```text
rank,symbol,score,mom3m,mom6_1,mom12_1,vol63,beta,adv60,maxdd252
1,...
2,...
...
```

### No UI yet

This milestone is deliberately command-line only.

Until the data and calculations are correct, UI development is wasted effort.

---

# 39. Suggested first implementation order — exact checklist

```text
01 [ ] Add quant/ package
02 [ ] Add data/ gitignore entries
03 [ ] Implement Dhan instrument-master downloader
04 [ ] Implement NSE legacy bhavcopy parser
05 [ ] Implement NSE UDiFF bhavcopy parser
06 [ ] Normalize both into one schema
07 [ ] Persist Parquet
08 [ ] Add DuckDB query helpers
09 [ ] Backfill 2018-present first for fast iteration
10 [ ] Build eligible-universe function
11 [ ] Implement returns
12 [ ] Implement momentum features
13 [ ] Implement risk features
14 [ ] Implement liquidity features
15 [ ] Implement robust z-score normalization
16 [ ] Implement factor_v1 score
17 [ ] Generate latest ranking CLI
18 [ ] Write feature unit tests
19 [ ] Backfill 2010-present
20 [ ] Add corporate-action adjustment
21 [ ] Build backtest engine
22 [ ] Add transaction costs
23 [ ] Run walk-forward validation
24 [ ] Freeze factor_v1 specification
25 [ ] Add Mongo recommendation models
26 [ ] Publish latest validated results
27 [ ] Add /quant UI
28 [ ] Add daily scheduled job
29 [ ] Repair simulator P&L
30 [ ] Start live forward test
31 [ ] Add fundamentals
32 [ ] Test Elastic Net
```

---

# 40. Minimal environment variables

Existing:

```text
MONGODB_URI
MONGODB_DB_NAME
GEMINI_API_KEY
```

Quant pipeline:

```text
QUANT_MONGODB_URI=${MONGODB_URI}
QUANT_DB_NAME=${MONGODB_DB_NAME}
QUANT_DATA_DIR=./data
```

Optional later:

```text
DHAN_CLIENT_ID
DHAN_ACCESS_TOKEN
```

These are **not required** for v1 market data.

---

# 41. Zero-cost operating model

## Research/backtesting

```text
your computer
DuckDB
Parquet
Python
```

Cost:

```text
₹0
```

## Website

Continue existing:

```text
Vercel
MongoDB Atlas
```

assuming your current free/existing tiers remain sufficient.

## Daily automation

Use either:

```text
local Task Scheduler/cron
```

or:

```text
GitHub Actions public-repo workflow
```

## Market data

```text
NSE public downloads
NSE filings
RBI
Dhan free instrument master
```

Incremental data cost:

```text
₹0
```

---

# 42. What NOT to build now

To stay free and maximize research quality, explicitly postpone:

```text
real-time recommendation recalculation
tick database
20-level market depth
option-chain ML
LLM stock picker
neural-network price prediction
Kafka
Redis
TimescaleDB
ClickHouse
Kubernetes
paid analyst-estimate feed
paid Dhan Data API
```

None of these are required to discover whether a medium-horizon Indian-equity ranking model has real value.

---

# 43. Model governance

Every model run must record:

```text
model_name
model_version
feature_version
data_as_of
data_sources
universe_size
excluded_count
code Git commit
run timestamp
status
```

Every recommendation must be immutable after publication.

If the model changes tomorrow, create a new model version rather than rewriting yesterday's result.

---

# 44. Data-quality gates

A security receives no recommendation if any essential check fails.

Example:

```text
insufficient history
invalid adjusted-price history
unresolved corporate action
zero/negative price
bad traded-value record
missing recent trading days
illiquidity below threshold
```

The engine should prefer:

```text
NO SCORE — DATA INSUFFICIENT
```

over a fabricated score.

---

# 45. Recommendation lifecycle

Use states:

```text
RESEARCH
CANDIDATE
ACTIVE
DOWNGRADED
EXITED
```

Suggested rules after validation:

```text
Candidate: score >= 85th percentile
Active entry: score >= 90th percentile and all risk gates pass
Hold: score >= 65-70th percentile
Downgrade/exit: score below threshold or risk/data gate fails
```

These thresholds must be validated; they are not fixed truths.

---

# 46. Avoid excessive turnover

For a 2–3 month strategy, calculate scores daily but rebalance less frequently.

Candidate research schedule:

```text
signal calculation: daily EOD
portfolio rebalance: fortnightly/monthly
risk/data exit: daily
```

This avoids paying costs simply because two stocks swap rank 24 and 25.

---

# 47. Frontend freshness requirement

Every Quant component must show:

```text
Data as of
Model generated at
Model version
Current/stale status
```

Never show yesterday's score with today's live price without making the timestamp difference visible.

---

# 48. Repo-specific final recommendation

Market Pulse already has enough product infrastructure to support a serious quant feature.

The project does **not** need a larger web architecture first.

Its biggest missing capabilities are:

1. a reliable historical Indian-market data layer;
2. point-in-time data semantics;
3. reproducible feature engineering;
4. a real backtester;
5. a model registry/version trail;
6. an immutable recommendation/outcome history;
7. explicit data freshness and failure states.

The first implementation should therefore be **data engineering and validation**, not frontend design and not machine learning.

The correct progression is:

```text
Free NSE data
    ↓
Clean historical database
    ↓
Momentum/risk/liquidity features
    ↓
Simple factor model
    ↓
10-15y backtest
    ↓
Walk-forward validation
    ↓
Daily published rank
    ↓
Market Pulse /quant page
    ↓
Forward simulator
    ↓
Point-in-time fundamentals
    ↓
Elastic Net
    ↓
Only then advanced ML
```

If the simple model cannot demonstrate a persistent post-cost edge, adding AI or more infrastructure will not solve the problem.

If it can, Market Pulse will have a genuinely defensible quantitative core built almost entirely from free public data.

---

# 49. Reference links used for this plan

## Repository

- `https://github.com/DakshUbhadia/Market_Pulse`
- `src/lib/constants.ts`
- `src/lib/actions/finnhub.actions.ts`
- `src/lib/actions/analysis.actions.ts`
- `src/lib/actions/momentum.actions.ts`
- `src/lib/actions/trading.actions.ts`
- `src/lib/actions/alerts.actions.ts`
- `src/lib/inngest/functions.ts`
- `src/app/api/quotes/stream/route.ts`
- `src/app/api/inngest/route.ts`
- `src/app/(root)/market-scope/MarketScopeClient.tsx`
- `src/components/analysis/MarketScopePanel.tsx`
- `src/components/analysis/MomentumRadarPanel.tsx`
- `src/components/analysis/OptionsRadarPanel.tsx`
- `src/components/analysis/TomHougaardAlert.tsx`
- `src/app/(root)/simulator/SimulatorDashboard.tsx`
- `src/database/models/*.ts`
- `next.config.ts`

## Free market/reference data

- NSE All Reports: `https://www.nseindia.com/all-reports`
- NSE Historical Index Data: `https://www.nseindia.com/reports-indices-historical-index-data`
- NSE Corporate Actions: `https://www.nseindia.com/companies-listing/corporate-filings-actions`
- NSE Financial Results: `https://www.nseindia.com/companies-listing/corporate-filings-financial-results`
- NSE Integrated Filing Financials: `https://www.nseindia.com/companies-listing/corporate-integrated-filing`
- NSE Shareholding Pattern: `https://www.nseindia.com/companies-listing/corporate-filings-shareholding-pattern`
- NSE FII/DII: `https://www.nseindia.com/reports/fii-dii`
- Nifty 500: `https://www.niftyindices.com/indices/equity/broad-based-indices/nifty-500`
- Dhan instrument master docs: `https://dhanhq.co/docs/v2/instruments/`
- Dhan historical data docs: `https://dhanhq.co/docs/v2/historical-data/`
- RBI data portal / DBIE: `https://data.rbi.org.in/`

## Dhan pricing caveat

Dhan currently documents the Data API as a paid subscription (₹499 + applicable taxes/month). Therefore this plan uses only Dhan's free instrument master for v1 and obtains EOD market data from free NSE sources.

---

# 50. Immediate next development task

Implement only these files first:

```text
quant/requirements.txt
quant/config.py
quant/data/http.py
quant/data/dhan_instruments.py
quant/data/nse_bhavcopy.py
quant/storage/parquet_store.py
quant/storage/duckdb_store.py
quant/pipeline/bootstrap_history.py
quant/tests/test_bhavcopy.py
```

Do not write the scoring model until a random sample of historical NSE dates can be downloaded, normalized, stored and queried correctly.

**Data correctness is milestone #1.**
