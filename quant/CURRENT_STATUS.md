# Current quant status

Updated 2026-11-18, Asia/Kolkata. This is the canonical implementation and
operations status. `PHASE_V1_STATUS.md` and `NEXT_PHASE_STATUS.md` are historical
snapshots. Completion percentages in the requested plan are estimates, not
acceptance evidence or investment performance.

## Source and validation

- Public main: `23490a75a6440ee2e84d3d64f36dd05620f78d6b` at the time checked.
- Public unit CI: [successful run on that commit](https://github.com/DakshUbhadia/Market_Pulse/actions/runs/44258077105).
- Current implementation is a local working-tree change, and is not covered by
  that public CI run. Local validation results are recorded below.
- Public live workflow dispatch was attempted but credential retrieval timed out;
  no remote live success is claimed. Local live-source smoke tests: 11 passed.
- Configured data: `D:/Market_Pulse_Quant_20261113/data`. The latest certified
  session remains 2026-11-17. The wall-clock EOD cutoff is not certification.

## Versions and invariants

| Policy | Current version |
| --- | --- |
| Model | `factor_v1_1.0.0` |
| Features | `factor_v1_features_1.0.5` |
| Total-return accounting | `ex_date_cash_1.2.0` |
| Evidence | `factor_v1_evidence_1.4.0` |
| Lifecycle | `pit_lifecycle_1.2.0` |
| Security transitions | `security_transitions_1.0.0` |
| Costs | `india_delivery_1.1.0` |

Factor weights, lookbacks, instrument IDs, universe rules and portfolio settings
are unchanged. There is no lineage-aware feature history. Accounting/evidence
versions change because the holdings contract and required sealed artifacts
change; an older baseline cannot authorize the new forward policy.

## Requirements and implementation assessment

| Plan sections | Implementation and evidence boundary |
| --- | --- |
| 1–3: baseline audit | Existing counts and percentages are historical observations. No new profitability, coverage or phase-completion claim is derived from them. |
| 4–5: identity | `identity/transitions.py` defines every requested field, transition type and verification level. Observed instrument IDs remain immutable. Only archived, hash-verified `VERIFIED_COMPLETE` rows can bridge holdings. Lineage conflicts, cycles, duplicate predecessors, missing dates, invalid multipliers and unsafe archive paths fail closed. Names, symbols, ISIN stems and prices never generate links. |
| 6: TIDEWATER | `review_security_transition` archives issuer ballot and record-date PDFs with hashes and writes `reports/security-transitions/tidewater-2016.json`. The ballot supports a candidate combined multiplier of four. Exact historical dissemination, ISIN validity and credit/listing/tradability remain unresolved. The March 16 old-ISIN ex quotation needs reconciliation. No normalized verified transition is invented. |
| 7–8: accounting | Mandatory transitions precede orders and valuation. Raw entitlements are converted through both securities' split factors; total cost basis and original recommendation identity survive. Holdings expose lineage, economic/tradable/pending units, cost basis and release date. Pending units cannot be sold before release. Missing successor valuation blocks. Features never consume lineage links. |
| 7: supported scope | Generic, fully evidenced one-successor splits, bonuses, ISIN replacements and mandatory mergers are supported. Separate predecessor legs, distinct recommendation lots, demerger cost allocations, complex reorganizations and chained pending entitlements require additional allocation accounting and explicitly block. A combined split/bonus with distinct release dates must not be collapsed into a falsely tradable lot. |
| 9–10: held blockers | New experiment directories preserve original frozen runs. Unresolved actual holdings stop the economic path; candidate inventories cannot excuse a missing holding value. No policy sensitivity is selected to avoid a blocker. |
| 11: CI | Public unit CI was verified on public main. Local smoke tests passed. Remote live dispatch could not obtain credentials; working-tree code still needs committed-head CI. |
| 12: status | This file is canonical. `write_current_status` emits `reports/current-status.json`, preserving report paths/hashes, local/public provenance, versions, baseline outcomes, cohort namespaces and coverage evidence. Missing reports remain unassessed. |
| 13–14: historical evidence | `security_transitions.parquet` joins the sealed artifact set. The same transition inputs propagate through comparison portfolios, all robustness variants and walk-forward windows. Normalized evidence and archived source bytes enter research manifests; new/changed evidence invalidates frozen inputs. V1 decisions mean continued research, with no public recommendation permission. |
| 15: forward launch | Still requires both sealed current-version baselines and positive V1 decisions with resolved held economics. Baseline completion hashes are frozen in cohort settings. Shadow and outcome replay use identical transition accounting. No cohort has been launched while prerequisites remain unmet. |
| 16: monitoring | `report_forward_cohort` checks frozen records and reports age, sessions, cycles, execution counts, 21/63 outcomes, mean/median excess, hit rate, close-NAV MAE/MFE, shadow return, matched TRI excess when available, drawdown, turnover, explicit charge drag, blockers and lifecycle events. Missing evidence stays null. No promotion occurs. |
| 17: backfill | Stage 1 (2024-01-01 through 2026-11-17) was attempted and resumed after fixing missing/non-text document URLs. `fundamental-backfill-status.json` records discovery windows, source counts, preserved versions, document hashes, parsing, review, timing, identity and checkpoint. Discovery completion alone does not establish usable fundamentals. |
| 18–19: fundamentals gate | Existing coverage evaluates every historical eligible period at 80% overall / 90% top-100 ADV, never an average. `fundamental_review_queue` uses dated eligibility/ADV and classifications, prioritizing liquid names, financials, parser failures and ambiguous revisions. Stage 1 parser stability remains unestablished; no 2020/2016 extension or Factor V2 activation follows from metadata discovery. |
| 20: costs | Existing dated component provenance and explicit historical proxies are retained. Three dated NSE charge circulars (2023, 2024, 2026) were archived with SHA-256 in `reports/historical-cost-evidence-review.json`; their historical terms mapping remains under review. No newly verified 2016-present cost schedule is claimed. Member-volume slabs, historical stamp duty/client assumptions and archived circular evidence still require research. |
| 21–26: sequencing | No ML, execution, optimization or public recommendation UI is added. Baseline completion, positive V1 evidence and actual forward accumulation remain prerequisites for later phases. Suggested PR names do not imply PR creation or approval. |

## Operational evidence

Original baseline experiments `20261118T050455-88e60ad4` (price) and
`20261118T051519-8f9bf362` (total return) remain unchanged and blocked on
TIDEWATER, 2016-03-17, predecessor ISIN `INE484C01014`. New attempts are tracked
in `research/experiments` rather than rewriting these experiments.

No successful baseline seal, `v1-decision.json`, forward cohort, daily forward
schedule, reliable fundamental window, Factor V2 activation or production
promotion is claimed. Starting a forward schedule before its baseline gate
would violate the requested sequencing.

Operational run results and final local verification are appended below after
the runs complete.

## Commands

Run from the repository root using the installed quant environment. Commands
write to `Config().data_dir`; explicit `--data-dir` overrides that location.

```powershell
python -m quant.pipeline.review_security_transition
python -m quant.pipeline.write_current_status
python -m quant.pipeline.run_backtest --from 2016-01-01 --to 2026-11-17 --estimate-historical-costs
python -m quant.pipeline.run_backtest --from 2016-01-01 --to 2026-11-17 --estimate-historical-costs --total-return
python -m quant.pipeline.backfill_fundamentals --from 2024-01-01 --to 2026-11-17
python -m quant.pipeline.backfill_fundamental_documents --from 2024-01-01 --to 2026-11-17 --limit 100
python -m quant.pipeline.audit_fundamental_coverage --from 2024-01-01 --to 2026-11-17
python -m quant.pipeline.fundamental_review_queue --universe <dated-universe.parquet> --to 2026-11-17
python -m quant.pipeline.report_forward_cohort --cohort factor-v1-2026q4-cohort-01 --to 2026-11-17
```

Historical-cost estimates are explicitly enabled for the diagnostic baseline;
this does not verify those costs or permit production use. Review commands and
coverage commands return nonzero when evidence remains unresolved or not ready.

`backfill_fundamental_documents` checkpoints each acquisition and preserves new document versions from already archived discovery metadata. The first bounded batch preserved 25 documents: 1 parsed, 24 need review; 20,828 document candidates remained unattempted at that checkpoint. Full Stage 1 document ingestion is **partial**, not complete. The next date-range stage remains gated on parser stability.

`scripts/run_quant_forward.ps1` prepares the daily paper flow for a supplied real session and sealed baseline pair. No scheduler job has been registered while launch prerequisites are unmet.


Final operational measurements:

- Full price attempt `20261118T073947-5fffae29`: BLOCKED by source-manifest
  change during implementation. It is not historical performance evidence.
- Frozen-score price diagnostic `20261118T075903-a55f4bc0` and total-return
  diagnostic `20261118T075905-2a3c8f58`: both BLOCKED on TIDEWATER,
  2016-03-17. These replay unchanged ranks and reconstruct the exact original
  trailing 63-session volatility from unchanged bars where the older compact
  exports omitted it. They do not create completion seals or replace full
  robustness/walk-forward evidence. Future prepared-score exports include that
  risk input. The first failed diagnostic is retained with its missing-column
  error rather than erased.
- Coverage audit: 35 monthly observations over 2024?2026; maximum usable
  consolidated coverage 0%, first reliable date null, NOT_READY.
- Discovery: 36 windows and 21,940 preserved metadata versions. Document
  acquisition is a separate, partial checkpoint (25 preserved, 1 parsed,
  24 needing review). Unsupported taxonomy/context handling requires review
  before a larger operational stage can be called stable.
- `reports/current-status.json`, `reports/held-blocker-replay.json`,
  `reports/fundamental-backfill-status.json`,
  `reports/fundamental-document-backfill-status.json`,
  `reports/fundamental-universe-coverage.json`,
  `reports/fundamental-review-queue.json` and the NOT_STARTED named-cohort report
  were produced in the configured data directory.

The requested phase remains **incomplete**: verified transition economics,
completed/sealed full baselines, V1 decisions, remote live CI, real forward
launch/scheduling, and full Stage 1 document ingestion remain outstanding.


Local validation: 291 tests collected; 280 non-integration tests passed and
11 live-source tests passed. After the final predecessor-entry guard, 38
focused transition, forward and simulation tests passed. Compilation,
dependency validation and Git whitespace checks passed. These results do not
substitute for CI on a commit containing the current working tree.
