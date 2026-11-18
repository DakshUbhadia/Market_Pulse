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
