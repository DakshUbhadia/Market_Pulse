# Evidence and champion/challenger phase

Epic: `quant-evidence-and-champion-challenger`. Reviewed November 18, 2026,
Asia/Kolkata, against `Market_Pulse_Next_Major_Phase_Evidence_Champion_Challenger.md`.
The document's completion percentages are estimates. This report distinguishes
implemented controls from evidence that has actually been acquired.

## Requirement assessment

| Document sections | Implementation / evidence |
| --- | --- |
| 1–3 | Existing V1, PIT factories, seven V2 blocks, covariance and research accounting were inspected and reused. No indicator or V1 weight changes. |
| 4–8, 49.4 | `data/source_health.py` and `pipeline/validate_source_health.py` expose archive, EOD and live dimensions, four independent global gates, and distinct failure classes. Research readiness audits archived inputs independently of a live calendar probe. Production publishing remains disabled without explicit model, monitoring and incident approvals. |
| 9–13, 49.5 | Existing blocked experiments remain untouched. TIDEWATER review reports `EVIDENCE_SEARCH_ACTIVE`. `research/evaluation_window.py` validates completed exhaustion audits and derives the next available session plus declared warm-up from the final mandatory held-event boundary. It stores the selection calendar, hash and `performance_used_to_choose_start=false`. No actual exhaustion or fallback window has been declared. |
| 14–15 | V1 retains its complete accounting, diagnostics, robustness and walk-forward seal. New runs also save `input-manifest.json` and target/fill diagnostics. `run_backtest --evaluation-window` supports separately declared limited-window runs, and the forward gate requires identical declarations for PRICE and TOTAL_RETURN. Existing statistical, economic and production validation levels remain separate. No real V1 baseline is newly sealed. |
| 16–19, 49.3 | `report_fundamental_acquisition` measures all discovered candidates, attempts, downloads, classifications, retryable/permanent failures and grouped denominators. Missing URLs are explicitly reviewable candidates. Explicit retries exclude permanent parser failures. Parser replay never enables V2. Acquisition is still incomplete. |
| 20–24 | Coverage uses historical eligible and ADV denominators. Certification requires at least 12 consecutive monthly cutoffs, every subsequent cutoff passing 80% / 90%, and no missing months. Quarterly diagnostics cannot certify a monthly interval. A real-data snapshot defect was repaired: discovery metadata no longer conflicts with its own parsed document at the same metadata identity, period and known-at time. Different documents and future revisions remain blocked. This is versioned `pit_fundamentals_1.1.0`. Share certification verifies archived evidence and preserves missing value features. Earlier expansion requires a recorded decision. |
| 25–28, 49.6 | `specs/factor_v2_1.0.0.json` contains the complete proposed policy, including formulas, missingness, normalization, capital, costs, risk and decision thresholds. It remains explicitly DRAFT because no certified research interval has been selected. The freeze CLI rejects drafts, captures code hashes, reserves one policy per version in its specification store, and rejects subsequent edits. The real runner requires exact clean-SHA public unit CI and prior filing/share continuity. All four arms now share dates, labels, costs, lifecycle and transition evidence. |
| 29–33 | Runner emits factor IC summaries, yearly/rolling IC, decile spreads, factor correlations, explicit missingness, four-arm metrics, cash/capacity/target-fill diagnostics and declared INR 10L/25L/50L/1Cr scenarios with cost stress. The risk allocation numerical fix is versioned `portfolio_risk_1.1.0`. Real historical arms have not run because their prerequisites fail. |
| 34–37, 49.7 | Immutable model cards and a locked, hash-chained registry implement all seven states. Historical validation verifies a sealed experiment and matching policy provenance. No champion is assigned at registration. Champion promotion requires the frozen forward sample policy, current cohort-bound monitoring, no unresolved incidents, and a model/monitoring-bound manual promotion record. |
| 38–40 | `run_registered_forward` prepares V1/V2 cohort collection after registry admission and actual after-close/before-next-open checks. It uses shared accounting, verified PIT source bytes, seven V2 contribution fields and immutable cohort settings. `report_forward_comparison` requires matched signal dates and comparable execution assumptions. No real cohort has been launched. |
| 41–42, 49.8 | Five monitoring modules cover fixed-bin feature drift, matured IC, coverage/parser failures, portfolio risk and session freshness. Monitoring also reports rank turnover and incidents. Its only action is review; no automatic retraining or promotion. |
| 43–48 | Elastic Net remains deferred, with zero weight. V2 has not passed its real historical gate and stable multi-year PIT feature coverage is not certified. Implementing or rejecting an untested ML model would violate this workstream's start gate. No Elastic Net result is fabricated. |
| 49.1–49.2 | The prior implementation SHA `269760f1aa12753547bb65b0e16c09f000dea406` has exact-SHA passing public unit CI. New implementation publication must be certified separately. Existing applicable version constants are public; new phase/risk versions are explicit. |
| 50–54 | The dependency sequence is enforced. The phase remains IN PROGRESS until the external evidence and operational gates below pass. Suggested PR names do not constitute independent research evidence. |

## Measured evidence

The configured corpus is `D:/Market_Pulse_Quant_20261113/data`. Its retained
readiness report identifies November 17, 2026 as the latest certified session;
the wall-clock EOD cutoff does not certify a newer date. Its pre-existing bounded
Stage 1 worker was observed running and was left undisturbed.

A repository-local acquisition snapshot counted **21,940 candidates**, **2,025
attempted**, **1,986 parsed without outstanding attempt review**, and **19,915
unattempted**: **9.23% attempt completion**. This includes candidates without
usable document URLs, which the previous download-only denominator excluded.
It is a timestamped observation of a changing corpus, not acquisition completion
or PIT universe coverage certification. Previously downloaded documents can
count as attempted even when not present in this particular checkpoint.

The three existing official TIDEWATER sources were downloaded and checksummed
again successfully. A further exchange-announcement retrieval timed out.
Search-index leads were recorded only as candidates. Credit, listing,
tradability, historical security validity and the valuation bridge remain
uncertified. The search remains ACTIVE; it is not exhausted. Both original
2016 experiments remain BLOCKED.

The initial fresh audit reproduced 0% usable coverage because discovery and
parsed-document representations were incorrectly treated as competing
revisions. After the selector fix, an audit against a frozen metadata snapshot
measures **35 monthly cutoffs**, with maximum usable consolidated coverage
**43.03%** and a **null reliable interval**. It remains NOT_READY. Source archive
checksums were verified separately from parser flags.

A fresh full foundation audit through November 17 returned READY independently
of a fresh calendar probe returning HTTP 403. The source-health report has
`historical_research_ready=true`, `live_source_health=DEGRADED` and
`production_publish_ready=false`. Its forward readiness is explicitly scoped
to the required November 17 session, without certifying November 18 inputs.

No complete verified-share corpus, reviewed/frozen real V2 specification,
positive V2 decision, champion, real forward evidence, or production publication
is claimed. The shipped JSON is a policy proposal awaiting the data interval
and recorded review; its review fields must not be relabelled to simulate
human approval.

Local operational artifacts are under
`data/evidence-champion-challenger/reports/`, including the acquisition snapshot,
public CI observation, separate live-test XML, TIDEWATER source hashes and active
search audit. They do not overwrite configured-drive reports or old experiments.

## Remaining execution gates

1. Require exact new-SHA publication/CI certification before real research;
   its result belongs in `reports/implementation-certification.json` and
   `reports/current-status.json`, independently of these committed notes.
2. Complete the official transition evidence search, or record a justified
   reviewed exhaustion audit before declaring any limited evaluation window.
3. Seal unchanged PRICE and TOTAL_RETURN V1 evidence under the same policy.
4. Finish Stage 1 classifications and certify filing and share coverage against
   the dated universe; establish the minimum reliable interval.
5. Select evidence-supported test dates, record specification review, freeze a
   version, and run the four untouched historical arms and capital scenarios.
6. Issue the historical decision, register eligible models, and collect real
   matched-date forward cohorts with monitoring.
7. Admit Elastic Net only after V2 PASS and stable multi-year coverage. A real
   rejection with zero weight is acceptable after the permitted experiment.

Local validation passed a full **340-test** non-integration regression and a
final **57-test** selection after the snapshot repair, covering **342 unique
cases**. The synthetic V2 run exercises all four comparison arms, capital
scenarios, shared accounting, coverage and seal writing and yields NO-GO.
Separate live checks returned **6 passed / 5 failed**, all failures HTTP 403.
Dependency, compilation and whitespace checks passed. Exact-SHA remote unit CI
is recorded separately in the machine certification report.
