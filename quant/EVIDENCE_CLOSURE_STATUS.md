# Evidence closure and model selection

Epic: `quant-evidence-closure-and-model-selection`. Reviewed November 19, 2026
(Asia/Kolkata) against
`Market_Pulse_Next_Phase_Evidence_Closure_and_Model_Selection.md`.
Phase status: **IN PROGRESS**. Software controls do not stand in for research
results, reviewed exhaustion, certified coverage or a mature forward sample.

## Specification assessment

| Sections | Implemented behavior and remaining evidence |
| --- | --- |
| 1-2 | Inspected the starting implementation and retained phase reports. The maturity percentages are estimates; no performance or completion claim is inferred from them. Existing Factor V1 weights and feature formulas remain unchanged. |
| 3 | Confirmed `f06add81a556cbd8fb422fd13015a2b9acbda8b9` was already published with successful exact-SHA public unit CI. `certify_implementation` now records all requested fields, local JUnit hashes/counts and dependency/compile/whitespace checks, and persists remote failure as NOT_CERTIFIED. Both historical runners require certification. The new working-tree changes require their own committed SHA and remote CI. |
| 4 | `data/source_requirements.py` declares dataset contracts for historical research, forward refresh, fundamental acquisition and publishing. Approved static/archive/API alternatives satisfy individual datasets, with verified provenance and current-session scope where required. `validate_source_health --dataset-observations` integrates these contracts while retaining independent historical/EOD/live/publishing gates. A blocked API does not revoke a usable official static dataset. |
| 5-6 | Existing VERIFIED_COMPLETE transition admission is retained. Exhaustion validation additionally requires explicit missing facts, document hashes, conclusion, dated review and performance-independence declarations. `record_evidence_search` checks archived bytes and writes an immutable audit. The evidence-only fallback remains separately frozen with a 252-session minimum warm-up. Original blocked experiments were not modified. TIDEWATER remains ACTIVE; no fallback is admitted. |
| 7-8 | `plan_fundamental_acquisition` combines audited missing-name/month cells, eligible identities, contemporaneous ADV and filing metadata. It greedily ranks potential marginal repairs with the specified top-100/threshold/continuity/entity priorities. Future filings cannot repair earlier dates; overlapping candidate repairs are discounted. Audits emit threshold gaps, name deficits, classified missing reasons and candidate IDs; share deficits stay null without a dated share assessment. |
| 9 | Acquisition reports expose every specified counter and explicit per-candidate terminal state. Missing source URLs are classified without inventing attempts. Both bounded document acquisition and Stage 1 accept a checksummed plan. Retryable attempts remain retryable, and unattempted URLs remain visible. Real acquisition is incomplete. |
| 10 | Existing 80% overall / 90% top-100 and 12-consecutive-month gates remain unchanged. Share reports expose requested coverage field aliases. Verified historical shares remain a separate requirement and current shares cannot fill history. No real share certificate was created. |
| 11 | Freeze now requires both filing and share reports. It recomputes monthly threshold continuity, requires a pre-OOS passing year, binds code SHA, reports and hashes, and records coverage-only date selection. Research entry rejects changed certificate source files. The proposed V2 policy remains DRAFT; no reviewer or dates were fabricated. |
| 12-14 | Existing four-arm shared accounting, factor diagnostics, capital scenarios and cost stress are reused. Added absolute minimum IC/IR and minimum valid-window proposals. Decisions distinguish BLOCKED, INCONCLUSIVE, NO_GO_V2 and GO_FURTHER_V2_RESEARCH. A short synthetic run now correctly yields INCONCLUSIVE. Real historical arms still cannot run. |
| 15 | PASS model cards must bind the historical seal and frozen forward sample policy. New V1 artifacts retain the original pre-run frozen specification and full manifest, allowing registry and release provenance checks. Registration still cannot assign a champion. No actual candidate was registered as validated. |
| 16-17 | Registered collection remains after-close/before-next-open. Matched comparison additionally verifies identical market/event file snapshots and execution timestamps. Cohort reports expose capacity, cluster and scoped incident assessments; absent evidence remains unassessed. Real cohorts were not backfilled or launched without the historical gates. |
| 18 | `monitoring/incidents.py` supplies an explicitly initialized immutable, hash-chained ledger for all nine classes. Opening/resolution CLIs preserve history. Monitoring consumes scoped incidents; promotion requires zero unresolved incidents and the current journal bound into monitoring. No automatic promotion/retraining. |
| 19 | `research/release.py` and `build_research_release` create new immutable release directories from historically validated candidates. Bundles retain the original experiment/seal, policy, card, coverage, metrics, factor/risk evidence, supplemental research inputs, environment and checksums. Verification works after relocation and optionally verifies original data bytes. No actual release was fabricated from blocked experiments. |
| 20-21 | Elastic Net is still unstarted with zero weight. The real V2 PASS and stable multi-year PIT feature gates do not pass. No untested rejection, tree/deep model, sentiment alpha or execution system was introduced. |
| 22-26 | Dependency order remains enforced. The phase cannot close until the external evidence, filing/share certification, sealed baselines, real V2 decision and forward-operation gates actually pass. |

## Observed evidence

The configured corpus is `D:/Market_Pulse_Quant_20261113/data`. Its retained
latest certified session remains **2026-11-17**. This work read that corpus and
wrote separate workspace-local artifacts in `data/evidence-closure/`.

The frozen diagnostic snapshot contains **21,940 candidates**, **3,125
attempted**, **3,085 parsed without outstanding review**, and **18,815
unattempted**: **14.24% attempted**. **3,238** candidates have terminal
classifications, including **113 MISSING_SOURCE_URL** candidates. The remaining
**18,702** have an unattempted source URL. These classifications do not certify
fundamental coverage or authorize historical expansion.

The audit uses **35 monthly cutoffs** and **9,143 dated eligible rows** from
the retained historical prepared universe. Peak usable consolidated filing
coverage is **43.44%**; the reliable interval is **null**. Source archive bytes
were checked before creating the local metadata snapshot. The acquisition
planner identifies **745** documents with an estimated **1,868** marginal
name-month repairs. These are possible repairs, not achieved coverage.
Superseded or conflicting same-time disclosures cannot claim a later repair.

A separate share audit exposes all 35 monthly denominators against empty
verified-share evidence inputs and returns NOT_READY. Its zero verified-share
coverage means no verified anchors/completeness evidence was supplied; it does
not estimate actual historical share counts or claim a complete shares search.

The highest-priority official NSE static XBRL was actually downloaded and
parsed as PARSED, with no review findings. Its bytes, normalized observation
and attempt report are retained separately. It was not inserted into the
original corpus or retroactively counted in the frozen coverage snapshot.

A fresh foundation audit returns READY through November 17 independently of
the API failure. The combined source-health report records historical research
and EOD readiness for that required session, live health DEGRADED, and
production publishing disabled. It does not certify November 18/19 EOD inputs.
The operational incident journal retains one OPEN SOURCE_OUTAGE with the live
test evidence; archived historical validation remains independent.

All three existing official TIDEWATER documents were retrieved and checksummed
again. Direct retrieval of the exchange announcement page timed out after
10 seconds. Search-index leads were retained as unverified. Credit,
listing/tradability, old/new ISIN validity and the valuation bridge remain
unproven. The immutable search audit remains EVIDENCE_SEARCH_ACTIVE. Original
PRICE experiment `20261118T050455-88e60ad4` and TOTAL_RETURN experiment
`20261118T051519-8f9bf362` remain BLOCKED.

Starting commit CI was verified at:
https://github.com/DakshUbhadia/Market_Pulse/actions/runs/44370186408.
That success certifies the starting commit, not these uncommitted changes.
Its original clean-tree certification is preserved separately from the
current working-tree certification report.

## Validation and artifacts

The final full non-integration regression passed **357 tests**, with
**11 live checks deselected** for separate execution. After the final
provenance, release and performance changes, the affected selection is rerun
and recorded in `reports/final-targeted-tests.xml`: **75 passed**. The final
revision-aware planner/registry selection passed **42 tests**, including rejection of
superseded-document repairs and mismatched model-card evaluation intervals.
Together the full and affected selections cover **358 unique cases**; the
deduplicated JUnit record is `reports/verified-unit-tests.xml`.
Live checks returned **6 passed / 5 failed**;
every failure is NSE API warm-up HTTP 403. Local integration results,
dependency, compile and whitespace checks are recorded independently in
`reports/implementation-certification.json`.

Important local reports under `data/evidence-closure/reports/`:

- `diagnostic-summary.json`, `fundamental-acquisition.json`,
  `fundamental-universe-coverage.json`, `fundamental-acquisition-plan.json`.
- `prioritized-acquisition-attempt.json` and the separate raw/normalized
  acquisition observation.
- `security-transitions/tidewater-2016.json` and the immutable
  `security-transitions/search-audit-20261119.json`.
- `implementation-certification-f06add8.json` for the starting clean commit;
  `implementation-certification.json` for the current working tree.
- `unit-tests-final.xml`, `final-targeted-tests.xml`, `live-tests.xml` and
  `current-status.json`.

## Remaining execution gates

1. Commit/publish the new implementation and certify its exact clean SHA.
2. Finish or formally exhaust the official TIDEWATER search; admit a fallback
   only with the complete real review and immutable evidence-only window.
3. Seal separate unchanged PRICE and TOTAL_RETURN V1 baselines and issue the
   historical decision.
4. Finish Stage 1 attempts/classifications; certify continuous filing and
   verified-share coverage. Neither gate currently passes.
5. Record real review, freeze the coverage-supported V2 interval/policy, run
   the four historical arms and all capital scenarios, and issue a decision.
6. Register passing models, package real research releases, and launch matched
   forward cohorts at their actual permissible signal times.
7. Collect sufficient forward evidence, monitoring and incident management;
   require manual promotion review.
8. Evaluate Elastic Net only after the V2 and multi-year feature gates pass.

No real OOS result, champion, production recommendation, mature forward
sample or completed evidence phase is claimed.
