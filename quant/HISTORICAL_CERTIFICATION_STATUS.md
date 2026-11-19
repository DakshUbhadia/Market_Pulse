# Data completion and historical certification

Epic: `quant-data-completion-and-historical-certification`. Assessed November
19, 2026 (Asia/Kolkata) against all 37 sections of
`Market_Pulse_Next_Major_Phase_Data_Completion_and_Historical_Certification.md`.
Phase status: **IN PROGRESS / EXTERNAL EVIDENCE REQUIRED**.

The document combines implementation requirements with historical-data and
elapsed-time milestones. Maturity percentages are estimates, not acceptance
evidence. The work below preserves that distinction.

| Document sections | Implementation and observed evidence |
| --- | --- |
| 1-4 | Retained the frozen V1 formulas, independent readiness/live/publishing gates, and dependency order. Reproduced the 6,460-cell discovery workload rather than accelerating the unchanged candidate list. |
| 5 / A | Independently verified `5697196bade75fe6ff0caa5ac951d37c6c0141cd` against successful public unit run [44489171483](https://github.com/DakshUbhadia/Market_Pulse/actions/runs/44489171483). Preserved the clean-tree certification, 381-case JUnit digest and separate six-pass/five-failure live evidence. Certification now exposes every requested field explicitly, archives successful SHA reports, requires assessed passing local JUnit, and preserves/checks its bytes when historical runners reverify. New code requires its own clean-SHA certification. |
| 6 / B | Added `data/fundamental_discovery_gap.py` and `pipeline/build_fundamental_discovery_gap.py`. JSON and Parquet contain one row per discovery cell, all specified columns, period/freshness bounds, candidate flags, reasons and causal priority. Future disclosures cannot set historical candidate flags. The 6,460/509 snapshot is reproduced; later snapshots may legitimately change. |
| 7 / B | Official source admission follows NSE, cross-listed BSE, then reviewed issuer IR. Fallbacks require recorded primary-source failure; BSE requires a verified security mapping; issuer sources require reviewed host ownership and exchange unavailability. Historical dissemination needs reviewed archived evidence; retrieval time cannot replace it. Source URLs, exchange, retrieval times and byte hashes remain archived. Aggregators are excluded. |
| 8 / B | Priorities use historical ADV, threshold proximity, consecutive gaps, then-known bank/NBFC classification and missing-month counts. Return columns do not affect priorities. |
| 9 / B | `discover_fundamentals_targeted` limits cells, instruments, HTTP queries and documents. It archives metadata before acquisition, parses, verifies source bytes, reruns PIT coverage and ceiling, and rebuilds gap/acquisition plans. It retains immutable batch directories and checksummed query history for subsequent batches. A source outage stops that route; parser failures remain reviewable. |
| 10-11 / B | Monthly ceiling reports include current and theoretical overall/top-100 coverage, threshold gaps and missing-cell/name counts. Existing 80%/90%/12-consecutive-month gates remain. The actual bounded batch selected 100 cells across 25 instruments, hit NSE HTTP 403 on its first query, acquired zero documents and retained 6,460 cells after replanning. No coverage gain was claimed. |
| 12 / C | Added the full capital-event schema and CLI. Bootstrapped 3,602 candidate events from retained official corporate-action archives, with copied/checksummed raw evidence. Ex-dates, proposal deadlines and parsed ratios are retained as leads; none is promoted into an actual effective/credit date or historical dissemination timestamp. Verified events: zero. |
| 13-14 / C | Certified share construction now requires starting and later known anchors, complete material-event interval evidence, and arithmetic reconciliation of every intermediate anchor. All declared event types are supported when terms are sufficient; unknown terms, missing dates, same-day ambiguity, lineage conflicts and unexplained discrepancies fail closed. An after-count cannot force equality. Every event needs a later reconciliation anchor. A broken chain disables Value. |
| 15-16 / C | Existing top-ADV share planning and the separate 80%/90%/12-month share gate remain. The 74 archived anchors still produce zero verified complete chains. Full Value stays mandatory for frozen V2; a diagnostic quality/growth study cannot silently redefine it. Fundamental features are versioned `fundamental_features_1.1.0` for the stricter share policy. |
| 17-19 / D | Rechecked public issuer disclosure/annual-report routes, visually reviewed all seven pages of three additional 2016 board PDFs, and attempted NSE/BSE/depository retrieval. The January document proposes the economics; May/August outcomes do not prove actual credit/tradability, ISIN validity or historical exchange availability. The bounded public-source review is formally `EVIDENCE_EXHAUSTED_UNRESOLVED`, explicitly attributed to automated Codex review, not independent human sign-off. No synthetic bridge was created. |
| 19 / D | Preserved original blocked 2016 PRICE/TOTAL_RETURN experiments. Froze a separate evidence-only evaluation declaration from the documented March 17, 2016 held-history boundary, next exchange session and 252-session warm-up: effective start **2017-03-28**. Calendar, audit, policy and declaration are hashed. Performance did not select the date. This declaration is not a completed baseline or a validated transition. |
| 20-22 / E | Existing matched PRICE/TOTAL_RETURN sealing, IC/decile/bootstrap metrics, robustness, benchmark comparisons and explicit PASS_RESEARCH / NO_GO / INCONCLUSIVE / BLOCKED decisions remain. New fallback-window baselines still require full real runs on a certified new SHA. No historical PASS or production validation is claimed. |
| 23-27 / F | Existing reviewed specification freeze, certified filing/share intervals, four mandatory arms, factor/portfolio/risk diagnostics, four capital scenarios and predeclared OOS decision rules remain. The draft feature policy reflects reconciliation. Real V2 is BLOCKED by failing coverage; no real four-arm output, GO decision or fitted weights were fabricated. |
| 28-31 / G | Existing sealed-candidate registration, matched forward snapshots, 126 signal sessions / six rebalance cycles / 30 distinct matured 63-session signals, scoped incidents, healthy monitoring and manual signed promotion remain mandatory. No ineligible real cohorts were launched. Elapsed forward evidence remains absent. |
| 32 / H | Elastic Net remains unstarted and gated on real V2 GO_FURTHER_V2_RESEARCH plus stable multi-year PIT coverage. No tested rejection, coefficient evidence or nonzero ensemble weight was manufactured. |
| 33-37 | Milestones remain ordered by evidence dependency. Software and review artifacts are concrete; data completion, real historical decisions and mature matched forward operation remain open. The phase is not represented as fully complete. |

The read-only retained corpus is `D:/Market_Pulse_Quant_20261113/data`; new
artifacts are in ignored `data/historical-certification/`. The latest retained
certified market session is November 17, 2026. No data in the retained corpus
or original blocked experiment directories was rewritten.

The committed `artifacts/historical-certification/phase-summary.json` binds
the local discovery, capital, share, governance and validation reports by
SHA-256. The baseline certification is committed beside it. Full source bytes,
Parquet, immutable batches, frozen window and JUnit files remain local.

Validation: **411 unit cases passed**, with 11 live cases deselected for
separate execution. Fresh live smoke returned **six passes / five NSE HTTP
403 failures**. Dependency, compile and whitespace checks passed. These are
software/source-health results, not historical model validation.

Next evidence milestones: obtain usable official missing filings and reviewed
capital-event chains; convert theoretical coverage into twelve passing monthly
filing/share cutoffs; run and seal both V1 bases under the declared window;
freeze and execute real V2 OOS; issue decisions; then admit matched forward
cohorts. Elastic Net follows only after an actual V2 PASS.
