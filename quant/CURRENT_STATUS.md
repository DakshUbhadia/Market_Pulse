# Current quant status

Updated November 25, 2026, Asia/Kolkata. Epic: `quant-completion-and-research-productization`.
This is the canonical summary. Earlier phase documents retain dated snapshots.
The [43-section assessment](PARALLEL_EVIDENCE_STATUS.md) and
[measured phase report](artifacts/parallel-evidence-completion/reports/parallel-evidence-completion-phase.json)
retain the prior execution evidence.

| November 25 work package | State | Acceptance evidence or blocker |
| --- | --- | --- |
| Exact implementation | `BLOCKED` | Base SHA `9ec2abd909bd665dcbb0cef0f8d5973a3c1962fd` has successful exact-SHA CI and an archived software certificate. Checkout changes require their own clean SHA, CI and certificate. GitHub push authentication is unavailable in this session. |
| Market refresh | `BLOCKED` | NSE calendar refresh returned HTTP 403 through the November 24 cutoff. A fresh read-only archive audit passed through November 17. The retained corporate-action digest matches across pandas 2.2 and 3.0 with canonical null encoding. |
| Filings | `BLOCKED` | Bounded 25-instrument, 100-cell pilot and official route checks added zero usable observations. The discovery deficit remains 6,460 cells. Archived evidence leads need dated consolidated exchange dissemination proofs. |
| Capital shares and joint coverage | `BLOCKED` | The verifier returned 3,602 candidates needing review. The November 17 archived V2 cross-section has zero complete joint rows across 339 names, including zero in the historical top 100. |
| Labels and archived diagnostic isolation | `VERIFIED_SOFTWARE` | The label contract retains censored and unavailable inputs, uses the exact next-open and 63-session endpoints, and includes availability in walk-forward purging. Archived diagnostics expose structural checks only. |
| V1 and V2 research decisions | `BLOCKED` | Independent TIDEWATER review is pending. The proposed fallback window remains inadmissible. V2 also requires its historical data and specification gates. |
| Elastic Net | `DEFERRED` | Training requires a genuine V2 GO decision and a stable multi-year PIT matrix. |
| Private application status | `VERIFIED_SOFTWARE` | Owner-scoped console and signed status projection. Production build, TypeScript and HTTP boundary checks passed. Hosted Mongo sync remains disabled. |
| Recovery and forward operation | `VERIFIED_SOFTWARE` | Daily and weekly writers share an OS lock. A controlled process exit released the lock. A copied 73-file synthetic release passed verification after corruption was detected and the damaged bytes were restored. Task Scheduler access was denied. Real forward launch and production promotion remain blocked. |

The November 25 regression passed **469 non-integration tests**. The separate
live-source smoke recorded **6 passes and 5 HTTP 403 failures**. The measured
local acceptance report is
`data/completion-enhancement/reports/acceptance.json`. It links JUnit hashes,
source responses, the market manifest and the joint coverage evidence to the
working-tree file hashes.

## Retained November 24 execution

| Area | Current state |
| --- | --- |
| TIDEWATER automated search | `EVIDENCE_EXHAUSTED_UNRESOLVED` |
| Independent human review | **PENDING**, intentionally preserved |
| Frozen 2017-03-28 fallback | `PREPARED_BUT_NOT_ADMITTED` |
| Final V1 PRICE/TOTAL_RETURN seals and historical decisions | `BLOCKED_BY_GOVERNANCE` |
| Real V1/V2 forward, V2 freeze/promotion, production publishing | `BLOCKED_BY_GOVERNANCE` |
| Actual diagnostic V1 replay | PRICE and TOTAL_RETURN both `BLOCKED_BY_DATA` on unvalued CAIRN, 2017-04-26 |
| Controlled V1/V2, risk and registry tests | 463 passing local case observations after documented targeted retests |
| Controlled V2 four-arm/capital run | Completed diagnostically; no real V2 decision |
| Portable diagnostic release | Checksum verification passed after relocation |
| Forward dry run | TEST_ONLY; four signal dates, 78 daily shadow observations, 3 matured 21-session and 1 matured 63-session outcomes |
| Monitoring dry run | Expected alerts from injected drift/data/risk/incident conditions; no automatic promotion |
| Usable filing/share interval | Not certified |
| Full V2 matrix | `INCOMPLETE`; verified Value missing for all 339 eligible archived-snapshot names |

Source implementation `42edfb0869dd8c3c49d094a8e494c66ee4967a79` is certified
for software implementation, with [successful exact-SHA unit CI](https://github.com/DakshUbhadia/Market_Pulse/actions/runs/44948049639).
This certificate is distinct from historical model validation. Evidence and
documentation successors require their own successful CI and clean-tree
certificate. The active `PUBLIC_MAIN_SHA`, `LOCAL_IMPLEMENTATION_SHA` and
`RESEARCH_CERTIFIED_SHA` are recorded in
`data/parallel-evidence-completion/reports/implementation-certification.json`.
Each archived certificate retains the SHA it actually certifies.

The retained corpus at `D:/Market_Pulse_Quant_20261113/data` remains read only;
its latest certified market session is **2026-11-17**. A fresh readiness audit
passed for archived diagnostic inputs; held-security valuation remains a
separate gate. The CAIRN merger requires complete equity, preference-share,
cash/dividend, timing and lineage evidence. Its new source packet does not
create a verified transition, change the evaluation dates or resolve TIDEWATER.
Both diagnostic attempts used identical prepared source inputs, source code
and score bytes. Neither reached a completed real robustness/walk-forward
inventory. Those paths passed controlled software tests separately.

The refreshed discovery queue remains **6,460 cells / 509 instruments**.
Broader usability failures total **8,328 name/month cells**. Usable overall
coverage peaks at **43.44%**; the best theoretical overall ceiling is **58.26%**
(50% top-100 at that cutoff), and the independent top-100 maximum is **51%**.
The 85%/95% discovery targets and continuous 80%/90% certification gates remain
unmet. All 3,602 capital-event candidates still need evidence review; the 74
existing anchors do not establish verified share chains.

The November 24 live refresh returned **4 passes / 7 source failures**:
four HTTP 403s, one NSE timeout/connection failure and two TRI-host DNS failures.
Both official NSE-base probes returned HTTP 403. The earlier November 22
6-pass/5-failure observation remains archived with its original date.

The phase remains incomplete where real evidence is unavailable. All diagnostic
and TEST_ONLY outputs remain ineligible for historical validation, accepted
seals, real forward evidence and promotion. Commands and artifact contracts are
documented in [README.md](README.md).
