# Factor V1 completion and forward paper testing

Current follow-on implementation and operational status:
[NEXT_PHASE_STATUS.md](NEXT_PHASE_STATUS.md). The text below preserves the preceding handoff.

Implementation review of `Market_Pulse_Next_Phase_Factor_V1_Completion_and_Forward_Testing.md`,
November 17, 2026 (Asia/Kolkata).

## Interpretation and boundaries

The user's request authorizes analysis and implementation. The document supplies
requirements and acceptance criteria; its example versions and branch names are
implementation guidance, not evidence of completed PRs or research results.
Changes remain in the current working tree. No remote publication, branch
protection change, automatic execution, Mongo publishing, V2 or ML is performed.

The repository already contained most of PRs 1–3. Existing feature, cost and
evidence versions were newer than the document's examples, so they were not
downgraded. Factor V1 weights and `MODEL_VERSION=factor_v1_1.0.0` remain frozen.
Feature, accounting, evidence and lifecycle versions were advanced where this
change alters artifact schemas or methodology. Policy versions are centralized
in `quant/version.py`.

The document's baseline policy and proactive risk-exit rule describe distinct
scenarios. The primary baseline remains `MANDATORY_ECONOMIC_EVENTS_ONLY`.
`KNOWN_EVENT_NEXT_OPEN_EXIT` explicitly enables proactive exits. Optional tender
participation and zero-recovery stress are separate labelled scenarios. No
later evidence supplies an earlier trade or an undocumented baseline recovery.
The instruction to continue V2 while collecting forward evidence remains subject
to the stricter unchanged-V1 decision gate and the phase's explicit V2 prohibition.

## Requirement review

| Document requirement | Implementation and status |
| --- | --- |
| Runtime versions and contracts | Central versions, including lifecycle; documented `lifecycle=` accepted by engine, robustness and walk-forward, retaining `lifecycle_events=` compatibility. Both names together raise an error. All 13 robustness variants and each walk-forward window preserve accounting inputs. |
| Test discovery and CI | `pytest.ini` already discovers all quant packages and keeps live tests opt-in. Duplicate test definitions were inspected; none needed removal. Both workflows already use supported v7 action majors ([checkout releases](https://github.com/actions/checkout/releases), [setup-python releases](https://github.com/actions/setup-python/releases)) and required checks. Remote green CI is unverified for these unpushed changes. |
| Compounded yearly excess | Existing compounded annual portfolio-minus-benchmark returns retained; regression named `test_yearly_excess_uses_compounding`. |
| Evidence methodology | Manifest policy version retained and bumped for positive median IC and explicit drawdown checks; median IC also gates statistical validation. Existing IC, decile, stress, cluster, baseline and year diagnostics retained. |
| Deterministic features | Row-level timestamps were already removed. Generation time stays in the feature manifest. Lifecycle exclusion/offer columns update the feature schema version. |
| Publishing disabled | `.env.example` and `Config` keep `QUANT_MONGO_PUBLISH=false`; paper stores are local files. |
| Lifecycle schema and ingestion | Existing schema, NSE inventories, BSE fallback and reviewed immutable imports retained. Raw source metadata now also records `fetched_at`, `source_exchange` and `sha256`. Verified zero-recovery events require documented mandatory zero economics. |
| PIT state machine | Publication time limits knowledge; pending statuses use the requested names. Relisting applies only when known and effective. Offer availability, price and dates are exposed. |
| Historical universe | Dated risk blocks entry and records `LIFECYCLE_RISK`, lifecycle status and entry reason. Existing positions resolve in accounting. |
| Held-security accounting | Mandatory cash and share conversions, successor identity, transferred cost basis, daily risk exits and unresolved-holding blocks retained/hardened. A suspended holding cannot use a stale positive print as an executable valuation. |
| Session order | State/economics → executable holdings and orders → dividend credits → valuation. Dividend entitlement uses prior-close positions; ex-date cash cannot fund the earlier open. |
| Sensitivity scenarios | Explicit documented-offer participation and hypothetical zero-recovery stress added. Offer settlements cannot acquire retroactive entitlement for later purchases. Baseline unresolved positions still block. |
| ESSAROIL | Existing dated original NSE notice and optional BSE exit-offer fixtures retained. Tests cover January 28 next-open exit, no earlier knowledge, no automatic tender and no invented fill. Synthetic execution bars test mechanics; they do not assert historical fill prices. Full universe lifecycle coverage remains unestablished. |
| Daily pipeline health | Existing lifecycle refresh order retained. Data-health now includes the lifecycle audit; invalid evidence fails health. Readiness already exposes lifecycle coverage separately. |
| Frozen experiments | Existing attempt ledger records blocked attempts. New `completion.json` seals the entire result, robustness and walk-forward tree only after successful completion. Forward gates verify all sealed artifact checksums. |
| Current snapshot / top 30 | Existing gated commands retained. Initial readiness failed and the subsequent full adjustment rebuild remains in progress, so no new ranking or defensible top-30 review is claimed. |
| 2016+ price and total-return baseline | Both commands attempted against workspace data; both recorded BLOCKED experiments. No OOS metrics or V1 economic decision are fabricated. |
| Immutable forward signals | New `quant/forward/signal_store.py` stores full versioned cross sections, weighted factor contributions, data/code provenance, generation time, next-open cutoff and batch hash. Atomic exclusive publication prevents replacement and concurrent overwrite. |
| Shadow portfolio | Reuses `run_backtest`, monthly rebalance timing, sizing, costs, lifecycle and dividend accounting. Frozen runtime settings must match. Previously sealed NAV corrections block for investigation. |
| Forward outcomes | Separate append-only 21/63-session records use next-open entry and the same single-security accounting, lifecycle/dividends and round-trip costs. Unresolved execution blocks outcomes. No change to original signal rows. |
| Daily forward pipeline | `run_forward_signal` refreshes, validates, builds, ranks, freezes, updates shadow and tracks outcomes. `update_forward_outcomes` can run independently. Both require real completed data. |
| Production validation | Forward summaries always remain `FORWARD_PAPER_ONLY`; overlapping horizons and short observation periods cannot automatically promote a model. |

## Operational evidence and blockers

All operational attempts in this implementation explicitly used workspace
`--data-dir data`. The user's `.env` points to a different drive; it was not
changed or written to.

Initially, workspace price partitions stopped at **2026-11-12**. The first
November 17 integrity rebuild stopped with:

```text
Corporate-action coverage is incomplete; adjusted research is unavailable
```

The independent November 17 readiness audit for a 2016-01-01 backtest returned
`NOT_READY` with:

- Generated calendar does not cover the requested date range.
- Adjusted-price baseline does not cover the required history through the latest session.
- Corporate-action inputs changed; rebuild adjusted prices.
- Lifecycle coverage remains `UNESTABLISHED`, with `lifecycle_data_ready=false`.

The price and total-return baseline attempts both stopped at the readiness gate.
Their frozen parameter records and blocked outcomes remain under
`data/research/experiments/`; the append-only ledger is
`data/research/experiments.csv`. Readiness details are in
`data/reports/research-readiness.json`. These data files are deliberately ignored
by Git. A verified individual fixture or downloaded inventory does not establish
complete point-in-time lifecycle coverage. Current lifecycle ingestion requires
reviewed dated event evidence; inventory refresh alone cannot certify coverage.

The missing November 13, 16 and 17 raw market sessions were subsequently fetched
successfully (3,727, 3,777 and 3,756 rows), along with market benchmarks and a
corporate-action refresh. The exchange calendar now covers all 4,187 expected
sessions from 2010 through November 17. Corporate actions now report coverage
from 2010-01-01 through 2026-11-17. The incremental adjusted-price stage correctly
refused a failed baseline and requested a full rebuild; a full rebuild was then
started. `data/reports/phase-v1-refresh.json` records the refresh outcome.
The two existing verified ESSAROIL events and their checksum-verified archived
bytes were copied from the configured dataset into workspace data; the lifecycle
audit now reports two verified events with no integrity errors, while correctly
retaining `coverage_status=UNESTABLISHED`.

At handoff, the full rebuild is still running in the background and has published
three of its 32 intermediate identity buckets. These are scratch outputs; the
complete daily adjusted corpus and final readiness are not yet certified. Follow
`data/phase-v1-integrity-rebuild.txt` for progress. The command writes final weekly
integrity/readiness reports after it finishes. No second rebuild should be started
against this data directory concurrently. The running command is:

```powershell
.\.venv\Scripts\python.exe -m quant.pipeline.weekly_audit --to 2026-11-17 --rebuild-adjusted --data-dir data
```

**Decision: BLOCKED / no V2 or ML promotion.** Historical economic evidence and
unseen forward evidence have not been collected by this implementation. Remote
unit CI must also be checked after publication. The five proposed PRs are not
claimed to exist.

## Validation performed

- Full non-integration suite: **231 passed, 11 deselected** on the final full run.
- One subsequently added baseline cost-parity gate test also passed; the final
  forward package run passed **15 tests**. The current collection contains
  **232 non-integration tests and 11 integration tests** across 39 test modules.
- The final combined feature/forward regression run passed **25 tests**, including
  deterministic feature bytes and offer columns for snapshots without lifecycle events.
- Live integration suite: **11 passed** against the actual official sources.
- Duplicate top-level test definitions: none.
- `pip check`, Python compilation and `git diff --check`: passed.
- These checks establish implementation behavior, not positive OOS performance,
  complete lifecycle coverage, remote CI or production validation.

## Resume historical work

Use the interpreter with `quant/requirements.txt` installed. This session created
an ignored root `.venv`; compatible NumPy 2.4.6 and pandas 3.0.5 were used after
Windows blocked a binary from a newer NumPy wheel.

Refresh missing market/calendar/corporate-action data and import independently
reviewed dated lifecycle events. Then, using the actual latest completed session:

```powershell
$asOf = 'YYYY-MM-DD'
.\.venv\Scripts\python.exe -m quant.pipeline.update_all --from 2026-11-13 --to $asOf --data-dir data
.\.venv\Scripts\python.exe -m quant.pipeline.weekly_audit --to $asOf --rebuild-adjusted --data-dir data
.\.venv\Scripts\python.exe -m quant.pipeline.check_research_ready --as-of $asOf --backtest-start 2016-01-01 --data-dir data
.\.venv\Scripts\python.exe -m quant.pipeline.build_features --as-of $asOf --data-dir data
.\.venv\Scripts\python.exe -m quant.pipeline.run_factor_v1 --as-of $asOf --data-dir data
```

Review the top 30 against the document's identity, IPO, corporate-action,
lifecycle, liquidity, volatility and price checks. Repair data or universe logic
when needed; preserve fixed factor weights. Refresh official TRI coverage if
needed, then run the document's two baseline commands with `--data-dir data`.
Inspect IC, median IC, deciles, costs, drawdown, turnover, year/cluster concentration
and simple-baseline competitiveness. A completed artifact alone is not a positive
economic result.

## Start forward paper collection after completed baselines

```powershell
.\.venv\Scripts\python.exe -m quant.pipeline.run_forward_signal `
  --as-of $asOf --data-dir data `
  --price-baseline '<completed price-return run directory>' `
  --total-return-baseline '<completed total-return run directory>'

.\.venv\Scripts\python.exe -m quant.pipeline.update_forward_outcomes --as-of $asOf --data-dir data
```

Run after data availability and before the next exchange open. Use
`--skip-data-update` only when the existing daily job has already refreshed data.
The future session schedule comes from dated exchange calendar evidence; unknown
special-session opening times block. Historical dates cannot be backfilled as
forward signals. Repeating a completed same-day command retains the original
signal timestamp and bytes.

Artifacts live under `data/forward/factor_v1/{signals,sources,shadow,outcomes}`.
Missing monthly cross sections or changed policy/settings block shadow replay.
Keep each versioned paper cohort separate when changing policies. Only the
explicit optional-offer sensitivity assumes participation; its payment requires
documented settlement timing. Stress write-offs remain labelled hypothetical.

Outcome entry is next-session open and exit is horizon-session close. Official
TRI has no modeled executable open; its comparison uses the preceding signal
close and records that convention. MAE/MFE use daily closing portfolio wealth,
including modeled costs and gross dividends, and explicitly identify that basis.
These are paper diagnostics. Distinct ranking rows, executed recommendations and
rebalance cycles are counted separately. No minimum number of weeks automatically
grants production validation.
