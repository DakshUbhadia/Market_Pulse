# Data coverage and model validation

Epic: `quant-data-coverage-and-model-validation`. Reviewed November 19, 2026
(Asia/Kolkata) against the 33 sections of
`Market_Pulse_Current_Changes_and_Next_Phase_2026-11-19.md`.
Phase status: **IN PROGRESS**. Feasibility estimates, working software and
passing software tests do not constitute validated investment results.

## Document assessment

| Sections | Implementation and evidence assessment |
| --- | --- |
| 1-2 | The supplied maturity percentages and acquisition counts are a dated starting snapshot, not acceptance criteria or returns. The previous controls are already committed as `dcbbc72c5fa841d8df86901a8d6314cffc333d44` and published on `feat/quant-evidence-champion-challenger`. Its unit CI completed successfully at https://github.com/DakshUbhadia/Market_Pulse/actions/runs/44480567401. |
| 3-4 | Certification records branch, exact SHA, clean tree, remote unit run URL/status, JUnit count and hashes, dependency/compile/whitespace checks, live counts/classes and timestamp. `PUBLIC_MAIN_SHA`, `LOCAL_IMPLEMENTATION_SHA` and `RESEARCH_CERTIFIED_SHA` are distinct fields in certification/current status. A rate-limited GitHub REST request can use an explicitly supplied public run URL; verification checks the complete commit link, unit workflow, completed success and URL, and archives the HTML hash. Dirty or uncertified historical runners remain rejected. A new commit requires its own verification. |
| 5 | Existing independent historical/EOD/live/publishing gates remain in force. Fresh live smoke returned 6 passes and 5 NSE HTTP 403 failures. No cached smoke substitution or exchange access-control workaround was added. |
| 6 | `report_fundamental_coverage_ceiling` calculates all requested monthly counts, overall/top-100 current and optimistic coverage, and ALREADY_PASSING / REACHABLE / UNREACHABLE_WITH_CURRENT_DISCOVERY. It verifies the original dated eligible identities and ADV, keeps PIT dissemination/revision/basis/duration/freshness rules, and prevents overlapping or ambiguous documents from inflating repairs. Optimistic parsing exists only in memory and cannot certify coverage. |
| 7 | `plan_fundamental_discovery_expansion` targets missing identity/month cells in unreachable months. It ranks top-100 gaps, threshold proximity, consecutive missing months, banks/NBFCs and historical ADV. It emits period bounds, required facts and official exchange/issuer routes. Changed coverage/universe inputs invalidate the plan. Actual discovery remains subject to source availability. |
| 8 | Acquisition plans bind the filing/attempt state and original input file hashes. A changed checkpoint/corpus or changed input file rejects reuse. Stage 1 requires a fresh plan and one bounded batch per call, followed by parse/normalize, PIT audit, ceiling recomputation and replanning. Zero-marginal-gain candidates are omitted. |
| 9 | Stage 1 freezes an immutable checksummed candidate declaration before its first batch. Reporting preserves that scope; disappeared candidates fail validation and new discovery does not silently redefine completion. The seven specified terminal states are used. Unreviewed parser findings and retryable failures are nonterminal. RETRYABLE_EXHAUSTED requires a recorded reason/reviewer/time and observed attempt count reaching the declared budget. Completion requires zero unattempted URL candidates in scope and every declared candidate terminal. Missing URLs remain classified without invented download attempts. |
| 10 | Historical-share functions now derive dated anchors from normalized paid-up equity capital / contemporaneous face value and replay verified splits, bonuses, buybacks, issuance and merger conversions. `build_share_history` verifies archived bytes and emits instrument, shares, known/effective dates, source hashes, verification status and value-feature validity. Complete capital-event interval evidence remains mandatory; current shares cannot fill history. `audit_share_history` exposes the existing 80% / 90% / 12-month share audit. |
| 11 | `plan_share_evidence` emits current verified-share coverage, an optimistic complete-chain ceiling, missing names with/without candidate anchors, and targeted actions. A candidate anchor alone cannot repair missing event-coverage intervals. Unknown event terms, future evidence and missing intervals remain invalid. |
| 12-14 | Existing reviewed immutable TIDEWATER search/exhaustion and transition admission controls remain. This bounded follow-up search did not establish credit/tradability and the old/new ISIN valuation bridge. TIDEWATER remains EVIDENCE_SEARCH_ACTIVE; no exhaustion review, VERIFIED_COMPLETE bridge or fallback window was invented. Original blocked 2016 experiments remain retained. |
| 15-16 | Existing PRICE / TOTAL_RETURN matched baseline gates, complete research artifacts and explicit V1 decision outcomes remain. Neither real baseline can be sealed until transition evidence or an admissible evidence-only fallback window is available. A historical PASS cannot authorize recommendations. |
| 17-21 | Existing V2 specification freeze requires passing filing/share intervals and recorded review before OOS; immutable policy binds the four arms, dates/identities, costs/accounting/benchmarks, factor/risk diagnostics, capital scenarios and decision thresholds. Real filing/share gates fail, so no new OOS output or decision was manufactured. |
| 22-23 | Existing evidence-eligible registry states, no champion at registration, sealed historical provenance and relocatable checksummed release bundles are retained. No blocked experiment is registered as validated or packaged as a real release. |
| 24-26 | Existing matched forward snapshots/timestamps/costs/event inputs, frozen 126-session / 6-cycle / 30-matured-signal minimum, monitoring, immutable incident history and manual promotion gates remain. No mature forward sample can be created by a software change. |
| 27-28 | Elastic Net remains gated on a real V2 GO_FURTHER_V2_RESEARCH decision and stable multi-year PIT features. No fitted challenger or untested rejection is claimed. No prohibited model families, sentiment alpha or automatic execution were added. |
| 29-33 | Dependency order is preserved. The measured bottleneck is discovery coverage and complete share-event evidence. The phase completion checklist remains open for external evidence, real historical decisions and forward observations. |

## Measured feasibility

The retained source corpus is `D:/Market_Pulse_Quant_20261113/data`; the
frozen filing/universe/attempt snapshot is `data/evidence-closure/inputs/`.
All new outputs are separate workspace-local files in
`data/coverage-validation/`. The corpus was read without rewriting its data.
The retained latest certified market session is **2026-11-17**.

All **35** monthly cutoffs are UNREACHABLE_WITH_CURRENT_DISCOVERY under the
unchanged 80% overall / 90% top-100 policy. The best theoretical overall
coverage is **58.26%** (February 2025); its top-100 ceiling is **50%**.
No theoretical 12-month reliable interval exists. At the November 17, 2026
cutoff both current and theoretical filing coverage are **0%** under the
declared freshness windows. This describes the retained snapshot, not an
exhaustive search of official filings.

The rebuilt acquisition plan contains **192** positive-marginal documents
with **1,868** potential name/month repairs. The former 745-document list
included overlapping documents contributing zero marginal repairs. The
remaining **6,460** cells across **509** distinct instruments require targeted
discovery rather than more downloads from that unchanged list.

The Stage 1 snapshot has **21,940** candidates: **3,222** terminal,
**16** unresolved parser reviews and **18,702** unattempted URL candidates.
Terminal classifications comprise 3,085 PARSED, 24 UNSUPPORTED_DOCUMENT and
113 MISSING_SOURCE_URL. Stage 1 is incomplete. No retry exhaustion or
permanent reviewer decision was synthesized to close it.

There are **74** dated paid-up-capital/face-value anchors with verified
archived source bytes. Complete capital-event interval inputs were not
supplied. The built **9,143** dated share rows therefore have **zero** verified
values; the complete-chain coverage ceiling also remains zero. Candidate
anchors are distinguished from complete candidate chains in the plan.

## Artifacts and remaining gates

The full non-integration suite passed **380** cases, with **11** live checks
deselected. After the final planned-document-only acquisition fix, all **61**
affected cases passed; the deduplicated JUnit evidence covers **381** unique
cases. Dependency, compile and whitespace checks passed. Separate live smoke
returned **6 passed / 5 failed**, all failures being NSE warm-up HTTP 403.

The small committed `artifacts/coverage-validation/feasibility-summary.json`
records measured counts and hashes of the complete local reports. Full
reports and source documents remain in ignored data storage:

- `reports/fundamental-coverage-ceiling.json`
- `reports/fundamental-discovery-expansion.json`
- `reports/fundamental-acquisition-plan.json`
- `reports/fundamental-acquisition.json`
- `reports/share-evidence-plan.json`, `share-history-coverage.json`,
  `share-history.parquet` and its input manifest
- `reports/unit-tests-final.xml`, `live-tests.xml` and
  `implementation-certification.json`

The implementation must be pushed and its exact SHA certified. Research then
requires actual targeted discovery, terminal Stage 1 classifications,
continuous filing/share certification, final reviewed TIDEWATER governance,
sealed matched V1 baselines, a reviewed frozen V2 policy, real four-arm/capital
results, eligible releases and sufficiently mature matched forward cohorts.
These are evidence and elapsed-time gates, not remaining software test claims.
