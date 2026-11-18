# Current quant status

Updated 2026-11-18, Asia/Kolkata. This is the canonical status. Earlier phase
files are historical snapshots. Estimates in audit documents are not measured
research completion or expected investment performance.

## Public and implementation provenance

The latest requested audit describes missing transition parameters. Inspection
of published commit `73adae00ae21bb07146908c18bc2a47257c2d761` and the clean local
checkout shows those parameters and their propagation already exist. The
remaining gaps identified below were implemented without changing Factor V1.

| Version | Public main at audit start (`73adae0`) | This implementation |
| --- | --- | --- |
| Model | `factor_v1_1.0.0` | `factor_v1_1.0.0` |
| Features | `factor_v1_features_1.0.5` | `factor_v1_features_1.0.5` |
| Accounting | `ex_date_cash_1.2.0` | `ex_date_cash_1.3.0` |
| Evidence | `factor_v1_evidence_1.4.0` | `factor_v1_evidence_1.5.0` |
| Security transitions | `security_transitions_1.0.0` | `security_transitions_1.1.0` |
| Lifecycle | `pit_lifecycle_1.2.0` | `pit_lifecycle_1.2.0` |
| Costs | `india_delivery_1.1.0` | `india_delivery_1.1.0` |

The implementation and its versions are committed together. Exact publication
and CI SHAs are recorded in configured `reports/current-status.json`; earlier
public CI does not certify a later commit or working tree.

## Audit requirements and implementation

| Sections | Assessment |
| --- | --- |
| 1?3 | Percentages remain audit estimates. The reported missing keyword contract was already fixed in public `73adae0`; no duplicate transition engine was added. |
| 4?8 | The engine, all 13 robustness paths and every walk-forward window accept identical transition evidence. The session sequence is documented in the engine: prior-close dividend entitlement; open; transitions; lifecycle settlements; permitted risk exits; sells; buys; dividend cash; valuation; daily accounting state. Transition ledger rows now expose economic, tradable and pending units plus all requested lineage/cost fields. Unvalued holdings still block. |
| 9?10 | Forward shadow and outcomes use the same accounting. Gates require `security-transitions.parquet` and the exact transition version. Completion hashes remain frozen. The standardized artifact name replaces the previous underscore spelling; older trees are retained unchanged. |
| 11?14 | Version claims distinguish the published audit-start commit from this implementation. `lifecycle_events` is the sole raw-input keyword; the old `lifecycle` alias is removed. Stored lifecycle ledgers retain their existing names. The new runner-contract test uses archived synthetic evidence and the real simulator, feature construction, full robustness, walk-forward, artifact writers and seal in both return modes. Infrastructure loaders/readiness alone use isolated synthetic test inputs. |
| 15?17 | TIDEWATER remains explicitly unresolved. The packet lists announcement availability, predecessor/successor validity, entitlement, credit, listing, tradability, multipliers and valuation bridge separately. Source inventories and first observed quotations are candidates, never historical availability or tradability proof. Generic verified single-successor accounting is retained. Multi-leg allocations, complex reorganizations and chained pending entitlements remain blocked. |
| 18?20 | Full historical reruns remain conditional on verified transition economics and exact-head CI. No Factor V1 weights, lookbacks, universe thresholds or portfolio settings change. No successful baseline or V1 decision is invented. Existing statistical, economic and production validation levels remain separate. |
| 21?22 | Cohort policy, signal records, settings, shadow replay and outcomes now freeze/check `security_transition_version`. Policy changes require a new cohort. The prepared daily wrapper remains gated by sealed baselines; no premature forward schedule is registered. |
| 23?27 | `report_fundamental_parser_stability` measures attempted/downloaded documents, parsing, timing and identity rates, failure groups by reason/entity/taxonomy/period, and unresolved dated top-100 ADV names. Taxonomy comes from checksum-verified archived XBRL namespaces. Each document batch emits a stability report. Empty or unsupported batches remain unassessed/unstable. Coverage still requires every proposed cutoff to meet 80% overall and 90% liquidity thresholds; averages cannot establish readiness. |
| 28?32 | Evidence-only historical shares and `value_feature_valid=false` for uncertain reconstruction are retained. No value factor, V2, ML or additional optimizer is enabled. Historical cost proxies remain explicit; three dated NSE charge circulars are archived but their historical terms mapping is not newly certified. |
| 33?37 | Publication and exact-SHA CI precede further historical research. TIDEWATER evidence must be complete before baselines can seal; sealed positive baselines precede real forward launch; stable Stage 1 data precedes earlier date ranges or V2. Suggested branch names do not constitute completed PRs or research evidence. |

## Measured operational state

Configured data directory: `D:/Market_Pulse_Quant_20261113/data`. Latest certified
session: **2026-11-17**. The wall-clock EOD cutoff is not certification.

Original frozen experiments `20261118T050455-88e60ad4` (price) and
`20261118T051519-8f9bf362` (total return) remain unchanged and blocked on
TIDEWATER, 2016-03-17, predecessor `INE484C01014`, observed successor
`INE484C01022`. The issuer ballot supports candidate combined entitlement
terms; exact historical dissemination, security validity and release/trading
dates are not proven. No `VERIFIED_COMPLETE` TIDEWATER bridge exists.

Earlier frozen-score diagnostics `20261118T075903-a55f4bc0` and
`20261118T075905-2a3c8f58` both reproduced that blocker. They are diagnostics,
not sealed full baselines. The failed source-change attempt and first compact
score replay error remain in their original experiment directories.

Stage 1 discovery preserved **21,940 metadata versions across 36 windows**.
The initial document batch preserved **25 documents: 1 parsed, 24 needing
review**, with 20,828 candidates unattempted at that checkpoint. Stage 1
acquisition is partial. The existing 35-month coverage audit reports 0% usable
consolidated coverage and a null first reliable date. Parser instability and
V1 prerequisites prevent date-range expansion.

No real cohort, forward evidence, completed full baseline, production
promotion, V2 activation or completed Stage 1 acquisition is claimed.

## Verification and commands

Local validation: 296 tests collected; all 285 non-integration tests passed.
Compilation, dependency validation and whitespace checks passed. Local live
checks and remote exact-SHA workflow results are recorded in the machine report. Passing synthetic transitions does not resolve TIDEWATER.

```powershell
python -m pytest quant/backtest/tests/test_security_transition_runner_contract.py -q
python -m quant.pipeline.report_fundamental_parser_stability --from 2024-01-01 --to 2026-11-17 --universe <dated-universe.parquet>
python -m quant.pipeline.review_security_transition
python -m quant.pipeline.write_current_status
```

All operational reports go to `Config().data_dir`. Source reports retain hashes
and missing evidence explicitly. Full baselines, real forward launch and
additional document/date-range stages remain pending their stated gates.


## Published implementation verification

Implementation `37c4dc8d37e02b0175ed448eddb20f5e04150a64` was pushed to main.
[Unit CI passed on that exact SHA](https://github.com/DakshUbhadia/Market_Pulse/actions/runs/44295830358).
The manually dispatched [live workflow failed](https://github.com/DakshUbhadia/Market_Pulse/actions/runs/44295984886):
6 passed, 5 failed because NSE session warm-up returned HTTP 403. The failures
remain failures; no source check is skipped or replaced with cached evidence.
Further research and acquisition remain gated by this external source-access
failure and the unresolved TIDEWATER economic bridge.

The existing 25-document parser report measured 4% parsing success, 100%
timing verification and 100% identity resolution. Failure reasons were 22
unsupported context/taxonomy cases and 2 unknown financial entity/consolidation
cases. All 100 dated liquidity names lacked a parsed document in the attempted
batch; this is a batch diagnostic, not full-universe coverage certification.

## Major-phase execution: source reliability and evidence recheck

On November 18, 2026, implementation began against local commit
`b086f38ff30cca36d0e838f419ffdecd45a088de`. The current working changes add
structured `LIVE_SOURCE_UNAVAILABLE` exceptions with HTTP status, modest request
jitter, language headers, and `Retry-After` handling before authorization-driven
session renewal. Renewal remains bounded to one attempt. A new
`quant.pipeline.probe_nse_source` CLI archives a unique report for each fresh
calendar smoke check, with source-code hashes and transport policy. This work
has not been published or verified by remote CI.

Fresh probes of both `www.nseindia.com` and the migrated `www.nseindia.in`
returned HTTP 403 during warmup. The complete live selection was executed in
two parts: `quant/tests/integration` returned 6 passed / 4 failed, and the
integration test in `quant/tests/test_calendar.py` also failed. All five failures
were HTTP 403 warmup failures. No live checks were disabled or reclassified.

The three existing official TIDEWATER sources were downloaded again and
archived. The issuer PDFs retain their previous checksums. The review still
cannot establish historical dissemination, old/new ISIN validity, credit,
listing/tradability or the valuation bridge. It remains `UNRESOLVED` with
`automatic_bridge_enabled=false`. The prior blocked baselines are retained;
rerunning their unchanged inputs cannot supply the missing evidence.

The configured corpus was inspected read-only. Its existing readiness report
still identifies November 17 as the certified cutoff; this is not a fresh
recertification. Parser stability remains 1 parsed / 25 attempted documents,
and the coverage report retains a null reliable fundamental start date.

Operational outputs for this execution are isolated under repository-local
`data/major-phase-execution/`, including `reports/major-phase-execution.json`,
source probes, raw responses and the fresh transition review. The execution
report records checksums of the configured corpus's existing reports and
baseline outcomes. It does not replace that corpus or certify a new baseline.

The non-integration suite passed 290 tests with 11 live tests deselected. Final
targeted transport/probe validation passed 16 tests, including one added after
the full suite was collected. Dependency, compilation and whitespace checks
passed. No new model, accounting or factor version was introduced.

Milestone 1 remains blocked by source access and missing TIDEWATER evidence.
Forward launch requires sealed acceptable baselines; Stage 1 acquisition remains
sequenced after launch. Historical expansion, V2, portfolio-risk research and
Elastic Net retain their documented prerequisites. No cohort or later research
milestone was activated during this execution.

## Expanded implementation after execution-sequence revision

The user subsequently authorized the changes needed to continue implementation.
Offline engineering, archived-data replay and Stage 1 document acquisition now
proceed independently of the V1 forward-launch milestone. Real forward launch,
completion seals and model promotion retain their evidence gates.

Implemented research components now include an exact versioned taxonomy
registry, statement-context resolver, offline archived-document replay,
industrial quality/growth/value features, bank-specific ratios, verified-share
coverage selection, seven equal-weight V2 blocks, and matched-universe V1
renormalization. Separate version constants identify the candidate feature,
model and portfolio-risk layers. V1's scoring policy is unchanged.

The parser supports explicit statement-basis text facts and rejects quarter/YTD
contexts whose reporting-date declarations contradict their XML periods. It
recognizes the exchange's `bank="B"` metadata and explicit banking/NBFC document
families. Incorrectly currency-tagged ratios remain missing. Four archived
industrial/bank/NBFC specimens now have checksum-pinned quarter expectations;
this does not claim the full named-company, annual and revision fixture corpus
or human approval required for broad parser certification.

The first revised offline replay parsed 25/25 documents. A subsequent live batch
downloaded 100 additional documents and initially parsed 87/100. Thirteen banking
metadata/taxonomy failures prompted the explicit banking mappings. Replay of
the complete 125-document archive then parsed **125/125** under the revised
implementation. These are bounded schema-parsing results; annual statements,
cash flow, historical shares, feature completeness and historical coverage are
separate requirements. Original normalized parsing outcomes are retained, so
their historical attempt counters differ from the new replay measurements.

Acquisition also exposed and fixed a Pandas 3 resume error: metadata-only hash
and status columns had been inferred as floats and rejected string document
hashes. The failed invocation retained its raw download before normalization;
the resumed invocation checkpointed the 100-document batch. Observation storage
now preserves an explicitly supplied parser version instead of replacing it
with `foundation-1`.

Static exchange archive requests no longer depend on web API cookie warm-up.
The web API's HTTP 403 failure remains explicit, while public documents can be
downloaded directly. A bounded Stage 1 supervisor was started with 100 documents
per batch and a 250-batch ceiling. It stops on source failures or a batch parsing
rate below 80%, checkpoints each document, and reports progress under configured
`reports/fundamental-stage1-acquisition.json`. Its first completed batch added
100 attempts with 98% parsing success; later progress is read from that report.
No historical range expansion is launched automatically.

The V2 runner requires reviewed, checksum-frozen specifications and matching
implementation hashes, sealed acceptable V1 baselines, source integrity and
every dated filing/feature coverage cutoff. It records all three comparison
arms, cost stress, factor IC, accounting outputs and a V2 decision. Blocked
attempts have an outcome and no seal. The supplied specification template is
explicitly `DRAFT`, with evaluation windows and portfolio capital unset.

The risk layer includes NumPy Ledoit-Wolf covariance, SciPy constrained
variance/turnover allocation, cash, stock/cluster/volatility/capacity constraints,
a prior-close simulator adapter and gated 12%/15% comparisons. Realized order
capacity violations prevent completion. Expanding/nested purged folds and
date-balanced weights are implemented; Elastic Net fitting and its nonzero
ensemble weight remain conditional on a future passing V2 decision.

Forward reports now honor their outcome/NAV cutoff and expose matched benchmark
return and information ratio when observations permit calculation. The prepared
forward wrapper remains available but no real cohort has been launched.

The exact commands and candidate formulas are in `quant/README.md`. Local
execution/replay artifacts and final test reports are retained under
`data/major-phase-execution/`. Software preparation does not establish positive
OOS evidence: TIDEWATER's historical transition is still unresolved, no new V1
baseline is sealed, no reliable fundamental interval or complete share corpus
has been certified, and no V2/risk model has been promoted. The complete phase
therefore remains in progress.

Final local validation passed 313 tests in the full non-integration regression
run and 21 tests in the final candidate/factory selection, covering **314 unique
non-integration cases**. The added end-to-end V2 test runs real PIT selection,
feature construction, coverage, three accounting comparisons and seal writing
with explicitly synthetic foundation inputs; it correctly produces a research
NO-GO rather than promotion. That test exposed and fixed the need to preserve
the prior month-close signal at the first OOS session's open. Dependency,
compilation and whitespace checks passed. All 11 live checks ran separately:
**6 passed, 5 failed**, each failure caused by NSE API warm-up HTTP 403.

The final implementation snapshot captured 535 checkpointed document attempts.
The latest completed supervisor batches parsed 100%. The worker remains bounded by its configured batch ceiling and
automatic source/parser stops. Fresh progress is available in the configured
supervisor report; `data/major-phase-execution/reports/major-phase-implementation.json`
retains a timestamped implementation, test and acquisition snapshot.
