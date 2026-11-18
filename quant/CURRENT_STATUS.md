# Current quant status

Updated November 18, 2026, Asia/Kolkata. This is the canonical status.
Earlier phase files are historical snapshots. Audit completion percentages
are estimates, not measured research completion or investment performance.

Epic: `quant-evidence-and-champion-challenger`. The detailed requirement
assessment, implementation paths and remaining gates are in
[EVIDENCE_PHASE_STATUS.md](EVIDENCE_PHASE_STATUS.md). Commands and artifact
contracts are in [README.md](README.md).

## Implemented controls

- Archive readiness, current EOD readiness and live API health are independent.
  Checksummed offline research does not depend on optional live API transport.
  Missing required EOD inputs still block forward refresh.
- Evidence-search states and an immutable validated-data-window policy are
  implemented. A fallback requires a completed reviewed exhaustion audit,
  every supplied mandatory held boundary, and at least 252 warm-up sessions.
  PRICE and TOTAL_RETURN must share the same declaration and unchanged V1 policy.
- Filing and share certification require 12 consecutive monthly cutoffs,
  80% overall and 90% top-100 ADV coverage, and every subsequent cutoff passing.
  The minimum interval must precede V2 OOS evaluation. Share archives are
  checksum-verified; unverified shares cannot enter value scoring.
- Acquisition reports include the complete candidate denominator, unattempted
  candidates, explicit outcomes and permanent/retryable failures. Earlier
  historical stages require a separate evidence-backed expansion decision.
- V2 research has all four arms: full V1, covered V1, raw V2 and risk-budgeted
  V2. It records factor diagnostics/correlations, missingness, target/fill
  ledgers, capacity/cash/risk comparisons and declared capital scenarios.
  A binding-constraint optimizer numerical issue was fixed and versioned.
- Immutable model cards and a hash-chained state registry gate historical and
  forward admission. Champion promotion requires historical PASS, frozen
  forward sample requirements, model-bound operational monitoring, no
  unresolved incidents, and a manual promotion record. Registration alone
  assigns no champion.
- Registered V1/V2 forward collection and matched-date cohort reporting are
  prepared. Feature/IC drift, coverage/parser health, rank turnover, portfolio
  risk and freshness monitoring produce review alerts without retraining.

The proposed `quant/specs/factor_v2_1.0.0.json` remains explicitly DRAFT.
Its formulas, missingness, normalization, costs, portfolio, risk, capital
scenarios and decision thresholds are specified. Certified dates and recorded
review are required before freezing; no real reviewed OOS result is implied.
Frozen specifications bind code hashes and reserve one policy per version.

## Actual evidence and blockers

Configured corpus: `D:/Market_Pulse_Quant_20261113/data`. Its retained
certification identifies **2026-11-17** as the latest certified session.
Wall-clock availability does not certify November 18 data.

The original experiments `20261118T050455-88e60ad4` (PRICE) and
`20261118T051519-8f9bf362` (TOTAL_RETURN) remain unchanged and **BLOCKED**
on TIDEWATER, 2016-03-17. The three existing official sources were downloaded
and checksummed again. Credit, listing/tradability, security validity and the
valuation bridge remain unproven. Additional exchange retrieval timed out.
The search is **EVIDENCE_SEARCH_ACTIVE**; no exhaustion, verified transition,
fallback window or successful baseline has been fabricated.

The existing bounded Stage 1 worker was observed running and left undisturbed.
A fresh local acquisition snapshot counted **21,940 candidates, 2,025 attempted,
1,986 parsed without outstanding attempt review, and 19,915 unattempted**:
**9.23% attempt completion**. This denominator includes missing-document
candidates. It is a dated snapshot of a changing corpus, not coverage
certification. The corrected fundamental audit spans 35 monthly cutoffs with
maximum usable consolidated coverage **43.03%** and no reliable PIT interval.
A real-data selector defect that treated discovery metadata and its own parsed
document as conflicting revisions was fixed in `pit_fundamentals_1.1.0`;
genuine conflicts and future revisions remain blocked. No verified historical
share corpus is present.

No real V2 decision, real forward cohort, champion, production promotion or
completed phase is claimed. Elastic Net remains deferred with zero weight:
the document permits it only after real V2 historical PASS and stable
multi-year PIT feature coverage. Untested ML is not labelled REJECTED.

## Provenance and validation

The prior 314-test implementation `269760f1aa12753547bb65b0e16c09f000dea406`
has [passing exact-SHA unit CI](https://github.com/DakshUbhadia/Market_Pulse/actions/runs/44345064718).
That workflow does not certify subsequent changes. The new real V2 gate
requires public unit CI on its exact clean implementation SHA.

Factor V1 model `factor_v1_1.0.0`, features `factor_v1_features_1.0.5`,
accounting `ex_date_cash_1.3.0`, transition `security_transitions_1.1.0`,
lifecycle `pit_lifecycle_1.2.0`, and costs `india_delivery_1.1.0` are
unchanged. Risk research is now `portfolio_risk_1.1.0`; the new controls
are `evidence_champion_challenger_1.0.0`.

The final full implementation regression passed **340 non-integration tests**.
After the snapshot repair, the final targeted selection passed **57 tests**,
covering **342 unique non-integration cases** across both selections. Remote
exact-SHA CI and publication are recorded in machine reports separately.
All **11 live checks** ran separately: **6 passed, 5 failed**, each failure
caused by NSE API warm-up HTTP 403. No live failure was skipped or relabelled
as an archived success.

Repository-local execution reports are under
`data/evidence-champion-challenger/reports/`. They preserve the acquisition
snapshot, fresh source downloads/search status, public CI observation and
separate unit/live test results. They do not overwrite old experiments.
The complete research phase remains **IN PROGRESS**.
