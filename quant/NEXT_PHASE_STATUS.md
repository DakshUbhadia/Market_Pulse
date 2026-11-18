# V1 evidence, forward paper and PIT fundamental foundation

Implementation of `Market_Pulse_Next_Phase_V1_Evidence_Forward_and_Fundamental_Foundation.md`,
November 17–18, 2026, Asia/Kolkata (data cutoff November 17). This is the current implementation review;
`PHASE_V1_STATUS.md` preserves the preceding handoff.

## Interpretation

The user requested analysis and implementation. The selected document supplies
requirements, sequencing and acceptance criteria. Its completion percentages,
checked inventory, branch names and example commands are not evidence that
research runs, PRs, remote CI or validation have completed. Work is implemented
in the current working tree; no remote main change or PR publication is claimed.

The primary research scenario remains `MANDATORY_ECONOMIC_EVENTS_ONLY`. An
optional tender cannot become an automatic cash receipt. Downloaded exchange
inventories cannot establish historical announcement times. A blocked result is
retained as a blocker rather than replaced with a favorable sensitivity run.

Fundamental acquisition and coverage infrastructure is implemented now; its
operational backfill follows the document's forward-launch prerequisite. No
Factor V2, learned model, new portfolio constraint, automatic execution, Mongo
publication or public recommendation is enabled.

## Current measured status

- Configured corpus: 8,428,482 adjusted rows across 4,187 sessions;
  2016+ integrity and completed-session source health are READY through
  2026-11-17. Official Nifty 50/500 TRI have no missing required sessions.
- Current ranking: 2,760 feature rows, 328 scored names; all factual checks
  pass for the distinct top 30, bottom 30 and seeded random middle 30.
- Validation: 264 non-integration tests pass; 275 tests discovered in total,
  including 11 separate live-source tests. Compilation and dependency checks pass.
- Frozen baseline operations: price `20261118T050455-88e60ad4` and total return
  `20261118T051519-8f9bf362` both ran with full robustness requested and the same
  frozen input hash. Both are **BLOCKED** on TIDEWATER on 2016-03-17, without
  seals or a performance conclusion. The remaining evidence is described below.
- Full universe lifecycle coverage remains UNESTABLISHED. No forward cohort,
  reliable fundamental start date, V2 activation or production promotion is claimed.

## Requirement analysis and implementation

| Specification | Result |
| --- | --- |
| PR A: CI installation, pip check, compilation, collection, all quant tests | Existing workflow already includes all five required commands. Live tests remain manual. Existing checkout/setup-python v7 retained, verified against official releases. Public main's run 18 at `c27b49c` passed on November 17; these working-tree changes are not covered by that earlier run. |
| Pairwise clusters: 252 / 220 / distance 1.0 | Existing observed-overlap method retained. Named constants and exact `ASSESSED`, `INSUFFICIENT_HISTORY`, `INSUFFICIENT_PAIRWISE_OVERLAP` statuses added. Pair artifacts expose actual correlation distance. Missing prices remove both adjacent returns; no price fill. |
| Cluster sensitivity | Existing 0.8 / 1.0 / 1.2 diagnostics remain in every full run. No hard holding cap is added. Insufficient pair overlap remains unknown exposure. |
| PR B: configured data directory and completed session | Operations use `Config().data_dir`, currently `D:/Market_Pulse_Quant_20261113/data`, with completed session 2026-11-17. The preceding workspace rebuild is separately identified; it is not substituted for configured-drive certification. |
| Historical identity boundary | Raw history remains 2010 onward. Verified observed ISINs start 2011-06-22, with a conservative first possible signal on 2012-06-25. Earlier unresolved rows remain excluded; no current-master repair. |
| Corporate-action identity drift found during required review | NSE supplied retired ISINs for later actions. The parser now reconciles a source identifier only with the same ISIN stem and a unique identity observed before and on the ex-date. Reported IDs/raw payloads are retained. Event-day transitions and cross-issuer symbol reuse are not bridged. `reconcile_corporate_action_identities` repairs normalized records while archiving their prior bytes. Feature version advances to `factor_v1_features_1.0.5`; model weights/lookbacks are unchanged. |
| PR C: lifecycle review queue | New `pipeline/lifecycle_review_queue.py`: held securities, historical top decile, eligible final-quote anomalies, then remaining inventory candidates. Accepts explicit dated holdings/scores/eligible files. Retained blocked experiment outcomes also identify actual held blockers, including older textual ledgers. |
| Final-quotation anomaly audit | New `pipeline/audit_security_lifecycle_gaps.py`: the five specified classifications, dated verified evidence and configurable five-session discovery grace. Scope is identities observed in EQ by the cutoff; final quotations are searched across all series so a series change is not falsely treated as a disappearance. Inventories without observed identities remain review-only. |
| No future lifecycle resolution | Future publication/effective dates do not explain an earlier missing quotation. A documented cash payment is not considered economically resolved before its settlement date. Optional offers do not resolve mandatory baseline accounting. |
| Lifecycle coverage reporting | Verified events, encountered/resolved/unresolved held events, top-decile events and yearly evidence counts are reported. Complete portfolio session dates avoid treating an already-sold position's stale last row as proof of ownership. Actual unresolved held events block sealing. Universe coverage remains independently `UNESTABLISHED`. |
| PR D: frozen model | Momentum 40%, relative strength 20%, low risk 20%, liquidity 20%; scoring, feature lookbacks and portfolio settings remain unchanged. |
| Current cross-section review | Ranking now writes deterministic, distinct top 30, bottom 30 and seeded random middle 30 samples. All ten requested checks and manual status begin `UNREVIEWED`; output generation does not claim human review. Replaced samples are archived with earlier ranking revisions. |
| Both full baseline artifact trees | Existing price/total-return runners, IC, deciles, stress, benchmarks, labels, clusters and walk-forward remain. A second manifest verification immediately before completion detects inputs changed while diagnostics/windows were being saved. |
| Review inputs survive a blocked baseline | Each experiment retains compact `prepared-scores.parquet`, `prepared-universe.parquet` and an input manifest before simulation. They are explicitly `PREPARED_INPUTS_ONLY`, with no completion seal or forward-evidence claim. The lifecycle queue can consume them to prioritize historical candidates even when simulation stops. |
| Completion seals | Seals publish exclusively and idempotently. Changing artifacts and calling the sealer again cannot replace a prior seal. A new experiment must use a new directory. |
| Sections 8–9: V1 go/no-go | Each successful baseline writes sealed `v1-decision.json`. It checks the predeclared positive IC/decile, performance, drawdown, turnover, 1.5x stress, year, label and sample-length checks; requires understood cluster exposure and net excess at least equal to the 12–1 momentum baseline. It adds no cluster cap and does not require production certification. Failure calls for investigation and leaves ML disabled. Legacy validation levels remain separately available. |
| PR E: real forward launch | Both sealed current-version baselines must cover the same dates, pass the V1 next-research decision, and have assessed, resolved held-event economics. Existing identical portfolio/cost/lifecycle settings, real session timing and immutable signal/outcome/shadow accounting remain. No production promotion is added. |
| Cohort admission and new cohorts | `cohort.json` freezes settings and all policy versions before a new signal is appended. Concurrent writers cannot introduce competing policies. Both forward CLIs accept `--cohort NAME`; named signals, sources, shadow portfolios and outcomes stay under separate `forward/factor_v1/cohorts/NAME/` stores. The existing unnamed store remains supported. |
| Overnight operation | Data health now evaluates freshness against the completed exchange session and reads the master snapshot's recorded acquisition date. A job spanning midnight does not falsely demand an unfetched next-day master; an actually stale master still fails. |
| PR F: bounded historical filing acquisition | New `pipeline/backfill_fundamentals.py`: bounded windows, durable checkpoint/resume, revision overlap, optional full refresh, both quarterly/annual metadata, XBRL/iXBRL bytes, attachments, exact dissemination times, historical identity mapping, parser outcomes and SHA-256 provenance. An incomplete source window is retried before advancing. |
| Document version preservation | New `data/financial_versions.py` is shared by daily and backfill financial ingestion. Reused metadata/URLs serving changed XBRL bytes create distinct preserved versions. Unknown revision timing is flagged, never assigned the original release time. Detection invalidates use from the observation time onward while preserving earlier known snapshots. |
| PIT snapshot selector | New `features/fundamental_snapshot.py`: timezone-aware signal cutoff; dissemination and revision/availability must be known by that cutoff. Latest known revision is selected before usability, preventing fallback through a bad known revision. Ambiguous same-time versions and naive/uncertain timestamps remain unusable. |
| Period semantics | Actual durations classify quarter-only, YTD and annual; standalone/consolidated remain distinct. Additive quarters are obtained by comparable cumulative differencing, never YTD summation. Missing predecessors leave nulls. Stocks and ratios are excluded from differencing. |
| PIT historical shares | Evidence-only reconstruction supports split/bonus multipliers and verified absolute post-buyback/issuance/merger shares. It requires a dated published anchor, provenance and independently complete capital-event evidence. Future evidence cannot alter an earlier snapshot. Missing/ambiguous terms leave `value_feature_valid=false`; no current shares are projected backward. |
| Universe coverage and V2 boundary | New `pipeline/audit_fundamental_coverage.py`: each monthly/quarterly historical eligible denominator, usable numerator, liquidity cohort and bank/industrial/NBFC breakdown. Metadata/document archive hashes are verified. The first reliable date requires 80% universe and 90% liquidity coverage throughout the observed subsequent window. Missing universe dates cannot pass. No actual reliable window is invented. |

CI references: [checkout releases](https://github.com/actions/checkout/releases),
[setup-python releases](https://github.com/actions/setup-python/releases),
[public main workflow history](https://github.com/DakshUbhadia/Market_Pulse/actions).

## Coverage policy and practical limits

The default high-liquidity cohort is the top 100 dated eligible securities by
historical ADV60 (or all eligible names when fewer exist). It is configurable and
recorded in the report. The overall filing freshness ceiling is 550 calendar
days; quarter/YTD statements additionally require age at most 180 days.
These are explicit engineering defaults, not tuned alpha thresholds.

"Usable" here means a parsed schema fact with known timing, resolved identity,
unambiguous duration/basis/revision and verified archived metadata/document
bytes. It does not imply that every V2 factor's inputs are complete. V2 feature
completeness and alpha validation remain separate prerequisites. The historical
eligible universe is calculated with the unchanged daily rules and warmup;
only coverage-date rows are retained to bound the output's memory footprint.

Bank/industrial/NBFC percentages are null when the historical universe has no
corresponding dated classification. No current industry master is applied
backward. Unsupported or ambiguous XBRL contexts, including unparsed iXBRL,
remain archived with `NEEDS_REVIEW`; downloading bytes does not certify parsing.
Shares reconstruction accepts reviewed evidence; no complete historical share
anchor/capital-event corpus has been established by writing the selector.

Revision overlap re-polls the newest discovery windows. It cannot guarantee
detection of corrections to arbitrarily old source metadata; `--refresh`
revisits the complete bounded request. Original raw responses remain archived.

## Operational evidence

The configured-drive refresh loaded November 13, 16 and 17 bhavcopies with
3,727, 3,777 and 3,756 rows. Calendar and corporate-action state now cover
November 17; corporate actions preserve coverage beginning 2010-01-01.
The refresh performs a full adjusted rebuild because `update_all` was invoked
without incremental mode. Final integrity/readiness is not inferred from an
intermediate bucket or an earlier adjusted baseline.

The configured full rebuild finished with **8,428,482 rows and 4,187 daily
partitions**, covering 2010-01-01 through 2026-11-17. A fresh full-history audit
with requested backtest start 2016-01-01 then returned **READY**, with all six
checks true, 100% price-session coverage, no identity gaps after 2011-06-22 and
no errors. Weekly integrity state and `reports/next-phase-integrity.json` record
that certification. Because `update_all` already performed the full rebuild,
certification reused its completed output rather than performing a second
identical rebase.

The original refresh's final health check crossed midnight and returned
`NOT_READY`: it expected a November 18 master and marked November 17 sources
stale. That original report is preserved under `reports/revisions/`. After the
session-cutoff fix, incremental health against the freshly certified corpus
returned **READY**, with `freshness_as_of=2026-11-17` and no errors. The final
health result is `reports/next-phase-data-health.json`.

Both official Nifty TRI series were refreshed for the missing November 13–17
sessions. Direct reconciliation against the configured exchange calendar finds
2,717 observations per index from 2015-12-01 through 2026-11-17, with **zero
missing sessions**. Previous normalized history and raw provenance are retained.

The initial configured-drive stock-identity lifecycle scan produced **1,095**
final-quote review candidates. At that stage the retained experiment that failed on **ESSAROIL**, stable
identity `6c788a58-de33-575a-9f7a-188d887aa97a`, on **2016-02-10**, is priority 1
with `BLOCKED_HELD_ECONOMICS`. Its verified suspension notice and optional exit
offer do not prove mandatory cash settlement. The other 1,094 candidates were initially
priority 4 before historical eligible/decile/holding evidence was supplied. This
does not assert that every candidate was held or was eligible.

Reports are local and Git-ignored under the configured directory:

- `reports/security-lifecycle-gaps.{json,parquet}`
- `reports/lifecycle-review-queue.{json,parquet}`
- `reports/lifecycle-audit.json`
- `reports/research-readiness.json`
- `reports/fundamental-universe-coverage.{json,parquet}` when audited
- `state/fundamental_backfill/` when operational backfill is started

No new sealed baseline, positive OOS conclusion, forward cohort or reliable
fundamental start date is claimed merely from implementation or passing tests.
The earlier ESSAROIL run remains a retained blocked experiment. A newly
verified original NSE announcement (sequence 100282582, published December 7,
2015 at 17:42 IST) establishes delisting risk before the 2016 baseline starts.
The unchanged point-in-time entry policy therefore blocks new entry after that
publication. Its stated December 5 public-announcement date is not a delisting
or settlement date. No mandatory cash economics are inferred. The original
registry response, checksum and interpretation are retained in
`reports/essaroil-2015-announcement-review.json`; a regression test checks the
publication boundary and a 2016 cash-only simulation. Current baseline attempts
must establish whether this earlier source evidence clears the actual entry
problem. It does not retroactively settle the old run or establish complete
universe lifecycle coverage.

The first current snapshot contained 2,760 observed feature rows and 440 ranked
names. Its 90-name data review passed identity, observed EQ/company ISIN,
252-session history, liquidity, known lifecycle overlay, volatility, ADV,
duplicates and feature-completeness checks. It also found artificial continuity
breaks: CUPID on 2026-03-09 and PGIL on 2026-09-11. The source action records
existed but were attached to their retired ISINs. Independent exchange-filed
[CUPID bonus evidence](https://nsearchives.nseindia.com/corporate/CUPID_10032026132357_Intimation_of_Allotment_of_Bonus_Shares.pdf)
and [PGIL financial notes](https://nsearchives.nseindia.com/corporate/PGIL_05112026204305_72Outcome.pdf)
corroborate the respective 4:1 and 1:1 bonuses. No price jump is classified as
alpha or removed by changing factor weights.

The safeguarded reconciliation identifies **4,548 distinct action records**
with stale source ISINs. The original payloads, reported identifiers and prior
normalized files remain available; 569 transition observations remain explicitly
unassessed rather than being silently linked. Some retired source identities
precede the ISIN-bearing raw history. The incremental repair can omit an unmapped
ID only after scanning the entire raw range and proving the canonical identity
never appears; an observed unmapped identity still blocks. Every prior adjusted
partition's checksum was verified before resuming a failed preflight, which had
written no price partitions. The initial mechanical READY certificate predates
this data correction; the corrected corpus must pass certification again.

The historical repair subsequently recalculated **1,422,373 affected rows** and
published all **4,187 daily partitions**. The two reviewed bonus-date returns
now retain their actual economic moves: CUPID **+13.87%**, PGIL **-0.13%**.
Fresh certification and feature/ranking regeneration completed after that
repair and the independently verified December 2015 lifecycle announcement.
The earlier snapshots are retained as superseded input versions. The current
`factor_v1_features_1.0.5` cross section has **2,760 observed feature rows and
328 complete ranked names**. The final top/bottom/random-middle review covers
30 distinct names per group: all factual QA checks pass, with no observed
adjusted daily return exceeding the declared 50% review threshold (maximum
36.00%). The minimum sampled history is 254 exchange sessions, minimum ADV60
is INR 50,625,162.55, and annualized volatility spans 0.2300?0.8779. These are
Codex source/data checks, not claimed human approval or exact IPO-date
verification. Ranking, sample and metadata checksums are preserved in
`reports/factor-v1-review-2026-11-17.json`. Full lifecycle universe coverage
remains unestablished.

## Frozen experiments and remaining evidence gates

The unchanged full price-return command ran against the certified configured
corpus from 2016-01-01 through 2026-11-17, including the new dated ESSAROIL
announcement. Experiment **`20261118T050455-88e60ad4`** is explicitly
**BLOCKED**, with full robustness requested. It passed the former ESSAROIL
entry problem and stopped on the actual held identity
`2b55953f-0ce3-5251-8deb-ad12a29e6700` (**TIDEWATER**, ISIN
`INE484C01014`) on **2016-03-17**.

The original source inventory contains a combined 1:1 bonus and face-value
split from INR 10 to INR 5 with ex-date 2016-03-16 and record date 2016-03-17.
It reports the later **VEEDOL / INE484C01030** identity, with no announcement
timestamp; the composite remains `NEEDS_REVIEW`. Raw bars show the old identity
through March 16 and `INE484C01022` beginning March 17. Prices also expose an
unreconciled event-date discontinuity. Those observations do not establish the
full dated conversion, credit, listing and executable share basis. The issuer
[postal ballot](https://www.veedolindia.com/sites/default/files/assets/pdf/pr-disclouser/PostalBallotNotice-Form28thJan2016.pdf)
corroborates the split and bonus terms, but does not by itself provide the
exchange ISIN activation, entitlement credit and listing bridge. The source
archive SHA-256 was independently checked; the full diagnostic is retained in
`reports/tidewater-2016-held-blocker-review.json`. No share multiplier, immediate
bonus availability, optional tender, cash receipt or zero recovery was assumed.
Mechanical READY covers session/OHLC/input integrity; it does not certify every
historical economic continuity or substitute for held-event accounting.

The blocked experiment retains **605,008** dated eligible rows across 1,044
identities and **602,188** score rows across 1,034 identities, including warmup
history. Their manifests explicitly say `PREPARED_INPUTS_ONLY`: no completion
seal, complete performance report or forward claim follows from those inputs.
The corresponding total-return attempt
**`20261118T051519-8f9bf362`** also returned **BLOCKED** for the same held
identity and date. Both used input SHA-256
`b1dda1d759e2af99327ac4a224736fd4c2962b7a2854815f78e140735c94db4d`.
Their separate frozen parameters, prepared inputs and outcomes are retained;
neither produced a completion seal. IC/deciles, stress, benchmark and
walk-forward conclusions are not claimed from simulations that stopped before
completion. `reports/next-phase-execution-summary.json` consolidates both
actual outcomes, checksums, ranking checks and coverage measurements.

The lifecycle queue now consumes those historical populations. Of **1,100**
review rows, priorities are **2 held blockers**, **134 historical top-decile**,
**68 other historically eligible**, and **896 remaining/inventory** candidates.
The two priority-1 entries include the legacy ESSAROIL experiment and the new
TIDEWATER failure; the legacy holding is not claimed settled. The held audit
reports one observed unresolved valuation for the current blocked experiment,
with scope `ONE_ACTUAL_BLOCKED_HOLDING_ONLY_NOT_COMPLETE_HOLDINGS` and full
held-event assessment still `UNASSESSED`. Verified events total three; complete
universe lifecycle coverage remains `UNESTABLISHED`.

The actual monthly fundamental audit covers **131 periods**, January 2016
through November 17, 2026. Every period has a nonempty dated eligible denominator
(98?339 names); usable coverage and top-liquidity coverage are **0% throughout**.
Bank/industrial/NBFC percentages remain null because historical classifications
are not supplied. `first_reliable_fundamental_signal_date=null`, status
`NOT_READY`, and fundamental scoring remains disabled. This measures the empty
normalized filing corpus against the historical universe, not against today's
constituents. Reports include the universe and calendar checksums.

Both sealed, current-policy, acceptable baseline decisions are required before
a real paper launch. The November 17 after-close/before-next-open window has
already expired, so a later successful launch must use its actual eligible
session rather than backdating November 17. Operational fundamental backfill
remains sequenced after that real cohort is running. Code for acquisition,
resume, coverage and PIT selection is ready; historical evidence, forward
outcomes and a reliable fundamental window are not fabricated to fill the gap.

## Commands and sequencing

Use the interpreter with `quant/requirements.txt` installed. Omitting
`--data-dir` deliberately uses the actual configured directory. Do not launch a
second adjusted rebuild concurrently against it.

```powershell
$asOf = '2026-11-17' # replace only with a real completed exchange session
.\.venv\Scripts\python.exe -m quant.pipeline.update_all --from 2026-11-13 --to $asOf
.\.venv\Scripts\python.exe -m quant.pipeline.reconcile_corporate_action_identities --to $asOf
.\.venv\Scripts\python.exe -m quant.pipeline.weekly_audit --to $asOf --rebuild-adjusted
.\.venv\Scripts\python.exe -m quant.pipeline.check_research_ready --as-of $asOf --backtest-start 2016-01-01
.\.venv\Scripts\python.exe -m quant.pipeline.lifecycle_review_queue --as-of $asOf
.\.venv\Scripts\python.exe -m quant.pipeline.build_features --as-of $asOf
.\.venv\Scripts\python.exe -m quant.pipeline.run_factor_v1 --as-of $asOf
.\.venv\Scripts\python.exe -m quant.pipeline.run_backtest --from 2016-01-01 --to $asOf --estimate-historical-costs --hypothesis 'Frozen Factor V1 price-return baseline'
.\.venv\Scripts\python.exe -m quant.pipeline.run_backtest --from 2016-01-01 --to $asOf --estimate-historical-costs --total-return --hypothesis 'Frozen Factor V1 total-return baseline'
```

Inspect `*-review-sample.csv` and repair only data/universe defects. For lifecycle
priority 2/3 use the queue's `--scores` and `--eligible` inputs; use `--holdings`
for a full retained actual holdings history. A blocked-outcomes-only assessment
is explicitly labelled and is not full held-universe coverage.
The experiment's `prepared-scores.parquet` and `prepared-universe.parquet` are
appropriate historical queue inputs after a blocked simulation. They are not
sealed baseline or unseen forward artifacts.

After **both** successful sealed baseline decisions, at an actual after-close,
before-next-open time, use the existing `run_forward_signal` command with
`--price-baseline` and `--total-return-baseline`. Use `update_forward_outcomes`
daily. Never backfill an expired date to manufacture unseen evidence. Model,
feature, accounting, cost, lifecycle or portfolio changes require a new cohort.
Supply the same `--cohort v1-paper-20261117` to both commands when using a named
cohort. Reusing a name with different versions or settings is rejected before
any conflicting signal is written; choose a new name after a policy change.

After a real forward cohort is running:

```powershell
.\.venv\Scripts\python.exe -m quant.pipeline.backfill_fundamentals --from 2016-01-01 --to $asOf --window-days 30 --revision-overlap-days 14
.\.venv\Scripts\python.exe -m quant.pipeline.audit_fundamental_coverage --from 2016-01-01 --to $asOf --frequency monthly --top-liquidity-count 100
```

The coverage CLI can instead read a retained dated universe with `--universe`.
It still requires the integrity foundation and archive verification. An empty
or partial month is reported unassessed rather than assigned a fabricated
denominator. No automatic V2 switch follows reaching the coverage thresholds.

## Validation

Regression coverage includes small missing-price gaps, insufficient pair overlap,
overlap-only distance, causal lifecycle discovery, historical series changes,
inventory identity uncertainty, held ownership across cash-only portfolio dates,
PIT revisions, unchanged metadata with changed document bytes, statement bases,
YTD differencing, capital evidence, date-level universe/liquidity coverage,
checkpoint resume, attachments, deterministic ranking samples, research decision
levels and exclusive completion seals. Local results and the final operational
status are recorded in this report and the configured execution summary.

The final implementation test suite passed **264 non-integration tests**, with
**11 live-source tests deselected**. Full collection discovers all 275 tests.
`pip check`, `compileall` and `git diff --check` passed. The two bonus cases were
also checked against the actual repaired dataset. These checks do not establish
positive historical alpha, completed forward evidence or production readiness.
