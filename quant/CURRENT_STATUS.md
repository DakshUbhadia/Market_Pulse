# Current quant status

Updated November 21, 2026, Asia/Kolkata. This is the canonical status.
Earlier phase files retain dated snapshots, not current certification claims.

Epic: `quant-historical-evidence-and-forward-validation`. Assessment of all
43 sections of the current specification is in
[HISTORICAL_FORWARD_VALIDATION_STATUS.md](HISTORICAL_FORWARD_VALIDATION_STATUS.md).
The previous phase is recorded in [HISTORICAL_CERTIFICATION_STATUS.md](HISTORICAL_CERTIFICATION_STATUS.md).
Commands and artifact contracts are in [README.md](README.md).

The previous coverage phase is retained in
[DATA_COVERAGE_STATUS.md](DATA_COVERAGE_STATUS.md); earlier evidence controls
are in [EVIDENCE_CLOSURE_STATUS.md](EVIDENCE_CLOSURE_STATUS.md) and
[EVIDENCE_PHASE_STATUS.md](EVIDENCE_PHASE_STATUS.md).

## Implemented and verified controls

- Exact-SHA certification separates public main, local implementation and
  research-certified SHAs. Public successful unit CI, a clean tree, passing
  local JUnit evidence, dependency, compile and whitespace checks are required.
  Historical runners reverify and reject missing or changed local test bytes.
  Live transport health is assessed separately from archived research inputs.
- The discovery-gap ledger reproduces 6,460 missing name/month cells across
  509 instruments. Priorities use historical ADV and availability information.
  Bounded official discovery archives raw responses and rebuilds PIT coverage,
  ceiling, acquisition and discovery plans after every batch. NSE, cross-listed
  BSE and reviewed issuer sources follow the prescribed hierarchy.
- Capital-event candidates are archived separately from verified event terms.
  Share chains require starting and later reconciliation anchors, complete
  event evidence and arithmetic reconciliation. Broken/unknown chains disable
  Value. Fundamental feature version is `fundamental_features_1.2.0`; share
  chains use `reconciled_share_chains_1.1.0`.
- Filing and share certification still require 80% overall, 90% top-100 ADV,
  twelve consecutive monthly cutoffs and all subsequent cutoffs passing.
- V1 retains separate matched PRICE/TOTAL_RETURN seals and explicit research
  decisions. Production validation remains separate from historical PASS.
- V2 retains a reviewed frozen policy, four comparison arms, capital scenarios,
  cost stresses and predeclared OOS decision criteria. Value remains mandatory.
- Sealed-candidate registration and matched forward cohorts retain the minimum
  126 signal sessions, six rebalance cycles and 30 distinct matured 63-session
  signals. Promotion requires healthy monitoring, zero unresolved scoped
  incidents and a manual signed decision. No automatic promotion or retraining.

## Actual evidence and open gates

Retained corpus: `D:/Market_Pulse_Quant_20261113/data`, latest certified market
session **2026-11-17**. New reports and source bytes are under
`data/historical-certification/`; retained corpus inputs remain read-only.

Starting commit **5697196bade75fe6ff0caa5ac951d37c6c0141cd** was independently
certified using successful exact-SHA public unit CI and 381-case local evidence.
That certification does not authorize changed code. The new implementation
must pass its own clean-SHA CI and certification.

Commit **52e1775975d594cc23bf64324a5d8305844ab4b1** also has a clean exact-SHA
certificate with **411 passing unit tests** and public successful unit CI at
https://github.com/DakshUbhadia/Market_Pulse/actions/runs/44496950926 . Its
certificate and test digests are now archived in
`quant/artifacts/historical-forward-validation/reports/`. Public main was
verified as **710bc6145157f01acc6f1a77ace985d909e1fa8b** at the start of this
work. Those are separately attributed prior-source facts; successor code
requires its own exact-SHA certificate after publication.

The actual discovery batch selected **100 cells / 25 instruments**, then
stopped on the first NSE warm-up **HTTP 403**. It archived the failed response,
recomputed coverage/ceiling and replanned: **6,460 cells remain**. All 35
monthly cutoffs remain unreachable with the current discovered corpus. Peak
usable filing coverage remains **43.44%**, and the best discovered ceiling
remains **58.26% overall / 50% top-100**. No reliable filing year exists.

The capital ledger contains **3,602 review candidates**, with verified source
bytes when available, and **zero verified capital-effective events**. Ex-dates
are retained as candidate dates, never promoted to actual credit/effective dates.
The **74** dated capital/face-value anchors still establish **zero verified
complete share chains**. Value research cannot pass the share gate.

TIDEWATER public-source search is formally **EVIDENCE_EXHAUSTED_UNRESOLVED**
after an explicitly attributed automated review. Three additional official 2016
board PDFs were downloaded and visually reviewed. They do not prove actual
credit/tradability, old/new security validity or historical dissemination.
Exchange/depository routes remain unavailable. The audit records its scope
and can be reopened on new official evidence; it is not independent human
sign-off or a verified economic bridge.

Original 2016 experiments `20261118T050455-88e60ad4` (PRICE) and
`20261118T051519-8f9bf362` (TOTAL_RETURN) remain **BLOCKED** and unchanged.
A separate evidence-only window is frozen with effective start **2017-03-28**,
derived from the documented held-history boundary and 252 exchange sessions
of warm-up. The window is not a completed backtest or baseline seal. Both
real V1 runs and their decision remain outstanding under the new certified SHA.

Independent human exhaustion confirmation and a separate immutable window
admission are now enforced by the runner. A pending review form and source
packet are available under this phase's `reports/security-transitions/`.
All **3,602** capital events remain **NEEDS_REVIEW** after the new verifier.
The required shared filing/share interval report is **BLOCKED**. V2 freeze
requires both that certified interval and an immutable human approval tied to
the exact specification, code and coverage. Promotion uses the same typed
governance framework. Software implementation does not close these gates.

The V2 specification remains **DRAFT**. Failing filing/share gates prevent
real OOS execution, historical registration and real V1/V2 cohort launch.
Forward observations remain absent. Elastic Net remains gated and unfitted;
no tested rejection or nonzero ensemble weight is claimed.

Final local validation: **437 unit tests passed**. The separately recorded
live smoke has **6 passed / 5 failed**, all failures NSE HTTP 403. Dependency,
compile and whitespace checks passed. Source hashes, JUnit digests and measured
phase evidence are archived in `quant/artifacts/historical-forward-validation/reports/`.
The committed status snapshot explicitly predates publication. The active
clean exact-SHA certificate is generated after public CI in
`data/historical-forward-validation/reports/implementation-certification.json`;
its SHA must match the code used for research. Software tests do not substitute
for historical coverage, investment evidence or elapsed forward observation.
