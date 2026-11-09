# Quant data foundation

Implements the immediate development task in section 50 of
`Market_Pulse_Quant_Engine_Implementation_Plan.md`. This is an ingestion milestone,
not a validated recommendation engine. Existing Next.js features are unchanged.

## Run locally

Requires Python 3.12 or newer. From the repository root (PowerShell):

```powershell
python -m venv quant/.venv
quant/.venv/Scripts/python -m pip install -r quant/requirements.txt
quant/.venv/Scripts/python -m pytest quant/tests -q
quant/.venv/Scripts/python -m quant.pipeline.bootstrap_history --from 2024-07-05 --to 2024-07-08
```

On Unix use `quant/.venv/bin/python`. A longer backfill uses the same command:

```powershell
quant/.venv/Scripts/python -m quant.pipeline.bootstrap_history --from 2018-01-01 --to 2026-11-06
```

`QUANT_DATA_DIR` defaults to `./data`; `--data-dir` overrides it. No API keys,
MongoDB credentials, paid market feeds, or application services are required.
The default end date is yesterday in Asia/Kolkata, avoiding a partial current day.
`--skip-instruments` skips the current Dhan mapping snapshot when only prices are needed.

Raw downloads and SHA-256/source/timestamp sidecars live in `data/raw/`.
Normalized prices live in `data/normalized/prices/year=YYYY/month=MM/DATE.parquet`.
Each daily partition is atomically replaced on rerun; valid raw caches avoid
redownloads. Run one writer per data directory. Checksums detect local corruption;
they do not authenticate or detect later exchange revisions of a cached file.
To intentionally refresh a source, remove its local cache file and rerun.

## Completeness and failure behavior

By default every calendar date is probed, including special weekend sessions.
404 responses are **unresolved**, not assumed holidays. Such runs exit 1 and
write an `INCOMPLETE` report under `data/reports/`. HTTP failures, corrupt archives,
wrong dates, schema changes, duplicate keys, and invalid required numeric fields
fail explicitly. Successful dates remain available for restart.

For measured coverage supply `--trading-dates path/to/sessions.txt`: a separately
verified exchange calendar containing one ISO date per line, including special
sessions. Coverage is loaded sessions / expected sessions within the requested
range. No 99.5% historical coverage claim is made without that calendar and a
completed backfill. Missing expected sessions still cause an incomplete run.

Both NSE eras have the same schema. Turnover is retained in source rupees, without
crore conversion. The source URL and archive checksum are repeated on normalized
rows. Keys are `(trade_date, symbol, series)` because a symbol can trade in multiple
series. The full cash archive is retained, not only current surviving EQ stocks.
Blank series and missing optional last prices are retained with `data_quality`
flags; neither is filled with invented data. A later eligible-universe stage must
require EQ and apply its own history/liquidity/action checks. No prices are adjusted.

## Query

```python
from quant.config import Config
from quant.storage.duckdb_store import query_prices

bars = query_prices(Config().prices_dir, start='2024-07-01',
                    end='2024-07-31', symbol='RELIANCE', series='EQ')
print(bars[['trade_date', 'close', 'volume', 'traded_value']])
```

## Identity and source references

- [NSE reports](https://www.nseindia.com/all-reports): legacy ZIPs before
  2024-07-08, UDiFF ZIPs thereafter.
- [Dhan instruments](https://dhanhq.co/docs/v2/instruments/): free detailed master.
  Actual detailed records use `UNDERLYING_SYMBOL` for the NSE ticker and
  `SYMBOL_NAME` for the company name. Stable UUIDs derive from ISIN; Dhan security
  IDs and unambiguous BSE cross-listings are retained. A future corporate-action
  identity registry must explicitly link ISIN changes; no automatic continuity
  is inferred across them. Today's snapshot must never filter historical prices.

## Remaining roadmap

The full 2010-present download and calendar reconciliation remain operational
work. Corporate-action adjustment, feature engineering, factor scoring, cost-aware
backtests, walk-forward validation, Mongo publishing, `/quant`, simulator repairs,
and forward testing follow the plan's later phases. Fundamentals and ML remain
deferred until their preceding validation gates pass.

Terminology policy: volume/price heuristics are not observed institutional flow;
scores are ranks, not calibrated probabilities. No output from this package is
presented as an investment recommendation or validated model performance.
