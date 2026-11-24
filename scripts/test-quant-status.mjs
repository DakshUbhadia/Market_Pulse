import assert from "node:assert/strict";
import { createHash, createHmac } from "node:crypto";
import { test } from "node:test";
import { isStatusOwner, parseStatus, syncDecision, verifyEnvelope } from "../src/lib/quant/status-contract.ts";
import { rankingDigest, readRankingPageNumber, verifyRankingManifest, verifyRankingPage } from "../src/lib/quant/investment-contract.ts";

const key = "a".repeat(64);
const now = Date.parse("2026-11-25T09:00:00.000Z");
const status = {
  schemaVersion: 1, runId: "b".repeat(64), gitCommit: "a".repeat(40),
  asOf: "2026-11-25T08:00:00.000Z", marketSession: "2026-11-17",
  authority: "STATUS_ONLY", validationStatus: "BLOCKED", humanReview: "PENDING",
  archiveReadiness: "READY", filingSources: "SOURCE_LIMITED", jointMatrix: "BLOCKED",
  fallback: "NOT_ADMITTED", implementation: "UNVERIFIED",
  v1Version: "v1", v2Version: "v2", featureVersion: "pit.1", costVersion: "cost.1", evidenceVersion: "evidence.1",
  sealHash: null, inputManifestHash: null, openIncidents: null, discoveryGaps: 6460,
  capitalCandidates: 3602, coverage: [],
};

function sign(value) {
  const data = Buffer.from(JSON.stringify(value));
  return { payload: data.toString("base64"), sha256: createHash("sha256").update(data).digest("hex"),
    signature: createHmac("sha256", Buffer.from(key, "hex")).update(data).digest("hex") };
}

function extended(overrides = {}) {
  return {
    ...status, schemaVersion: 2, ownerScope: createHash("sha256").update("owner").digest("hex"),
    publishingAllowed: false,
    details: {
      artifacts: { current: { sha256: "b".repeat(64), evidenceClass: "ARCHIVED_INPUT" } },
      metrics: { realCohorts: { value: 0, artifact: "current", asOf: status.asOf } },
      jointCounts: [], probes: [], filingQueue: [], capitalQueue: [], runs: [],
      riskPolicy: { max_weight: .05, max_cluster_weight: .25, adv_fraction: .01,
        target_volatility: .15, gross_exposure: 1, turnover_penalty: .001 },
      fallbackStart: null, tidewaterAudit: null, tidewaterExhausted: false,
      cairnObserved: null, fourArmDiagnostic: false, continuousJoint: false,
      eod: "UNASSESSED", scheduler: "UNASSESSED", certifiedSha: null,
      riskVersion: null, accountingVersion: null,
    },
    ...overrides,
  };
}

function signExtended(value) {
  return { ...sign(value), keyId: createHash("sha256").update(Buffer.from(key, "hex")).digest("hex").slice(0, 16) };
}

test("status is owner scoped", () => {
  assert.equal(isStatusOwner("owner", "owner"), true);
  assert.equal(isStatusOwner("reader", "owner"), false);
  assert.equal(isStatusOwner("owner", undefined), false);
  assert.equal(isStatusOwner(undefined, "owner"), false);
});

test("blocked and test-only snapshots carry status fields only", () => {
  assert.deepEqual(parseStatus(status), status);
  assert.equal(parseStatus({ ...status, authority: "TEST_ONLY" }).authority, "TEST_ONLY");
  for (const extra of [{ schemaVersion: 3 }, { recommendations: ["stock"] }, { fallback: "ADMITTED" },
    { humanReview: ["PENDING"] }, { sealHash: "f".repeat(64) }, { marketSession: "2026-11-31" }]) {
    assert.throws(() => verifyEnvelope(sign({ ...status, ...extra }), key, now), /schema/);
  }
});

test("new projections require the trusted owner and a recognized key", () => {
  const envelope = signExtended(extended());
  assert.equal(verifyEnvelope(envelope, key, now, "owner").status.schemaVersion, 2);
  assert.throws(() => verifyEnvelope(envelope, key, now, "other"), /owner scope/);
  assert.throws(() => verifyEnvelope({ ...envelope, keyId: "0".repeat(16) }, key, now, "owner"), /integrity/);
  assert.throws(() => verifyEnvelope(sign(extended()), key, now, "owner"), /owner scope/);
  assert.equal(verifyEnvelope(envelope, "c".repeat(64), now, "owner", key).status.schemaVersion, 2);
});

test("nested diagnostics, foreign provenance and contradictory publication fail closed", () => {
  const good = extended();
  for (const details of [
    { ...good.details, runs: [{ id: "20261122T091230-7b3bddc4", basis: "PRICE", start: null,
      end: null, codeSha: null, manifest: null, outcomeHash: null, meanReturn: 10 }] },
    { ...good.details, metrics: { localTestsPassed: { value: 469, artifact: "current", asOf: null } } },
    { ...good.details, jointCounts: [{ cutoff: "2026-11-17", complete: 2, eligible: 1, topComplete: 0,
      topEligible: 1, valueMissing: 1 }] },
  ]) {
    assert.throws(() => verifyEnvelope(signExtended({ ...good, details }), key, now, "owner"), /schema/);
  }
  assert.throws(() => verifyEnvelope(signExtended({ ...good, publishingAllowed: true }), key, now, "owner"), /publication/);
  assert.throws(() => verifyEnvelope(signExtended({ ...good, implementation: "CERTIFIED" }), key, now, "owner"), /Contradictory/);
});

test("signatures, digests and timestamp freshness are verified", () => {
  const envelope = sign(status);
  assert.equal(verifyEnvelope(envelope, key, now).stale, false);
  assert.equal(verifyEnvelope(envelope, key, now + 3 * 86_400_000).stale, true);
  assert.throws(() => verifyEnvelope(envelope, "c".repeat(64), now), /integrity/);
  assert.throws(() => verifyEnvelope({ ...envelope, sha256: "0".repeat(64) }, key, now), /integrity/);
  assert.throws(() => verifyEnvelope(envelope, key, now - 7_200_000), /future/);
});

test("sync rejects a changed snapshot at the same or earlier time", () => {
  const first = { sha256: "first", asOf: status.asOf };
  assert.equal(syncDecision(null, first), "ACCEPT");
  assert.equal(syncDecision(first, first), "DUPLICATE");
  assert.equal(syncDecision(first, { ...first, sha256: "changed" }), "REPLAY");
  assert.equal(syncDecision(first, { sha256: "new", asOf: "2026-11-25T09:00:00.000Z" }), "ACCEPT");
});

const investmentKey = "e".repeat(64);
const row = { instrumentId: "10000000-0000-0000-0000-000000000000", symbol: "TEST", rank: 1, percentile: 100,
  advInr: 3300000, volatility: 0.21, blocks: { momentum: 0.4, relative_strength: -0.2, low_risk: 0.3, liquidity: 0 } };
const samplePage = Buffer.from(JSON.stringify([row]));
const ranking = { schemaVersion: 1, authority: "RESEARCH_RANKINGS", ownerScope: rankingDigest("owner"),
  modelId: "v1-test", modelVersion: "factor_v1_1.0.0", codeSha: status.gitCommit,
  seal: status.runId, manifest: status.runId, gateDecision: status.runId, runId: status.runId,
  registry: { file: "00000001.json", sha256: status.runId },
  liveInputs: Object.fromEntries(["governance", "window", "incidents", "calendar", "pipeline"].map(name => [name, status.runId])),
  session: "2026-11-24", asOf: "2026-11-25T08:45:00.000Z", expiresAt: "2026-11-25T09:15:00.000Z",
  nextOpen: "2026-11-26T03:45:00.000Z", size: 1, proxyCosts: true, pages: [rankingDigest(samplePage)] };

function signRanking(value) {
  const bytes = Buffer.from(JSON.stringify(value));
  const signature = createHmac("sha256", Buffer.from(investmentKey, "hex"))
    .update("quant/investment/v1\0").update(bytes).digest("hex");
  return Buffer.from(JSON.stringify({ payload: bytes.toString("base64"), sha256: rankingDigest(bytes), signature }));
}

test("investment contract authenticates owner, integrity, and short eligible windows", () => {
  const envelope = signRanking(ranking);
  assert.deepEqual(verifyRankingManifest(envelope, investmentKey, "owner", now), ranking);
  assert.throws(() => verifyRankingManifest(envelope, investmentKey, "other", now), /manifest/);
  assert.throws(() => verifyRankingManifest(envelope, key, "owner", now), /integrity/);
  assert.throws(() => verifyRankingManifest(envelope, investmentKey, "owner", Date.parse(ranking.expiresAt)), /expired/);
  assert.throws(() => verifyRankingManifest(signRanking({ ...ranking, expiresAt: ranking.nextOpen }), investmentKey, "owner", now), /window/);
  assert.throws(() => verifyRankingManifest(Buffer.from(JSON.stringify(signExtended(extended()))), key, "owner", now), /envelope/);
  assert.throws(() => verifyEnvelope(JSON.parse(envelope.toString()), investmentKey, now, "owner"), /integrity/);
});

test("investment pages enforce manifest digests, exact rows and bounded pagination", () => {
  assert.deepEqual(verifyRankingPage(samplePage, ranking, 1), [row]);
  assert.throws(() => verifyRankingPage(samplePage, ranking, 2), /integrity/);
  assert.throws(() => verifyRankingPage(Buffer.concat([samplePage, Buffer.from(" ")]), ranking, 1), /integrity/);
  for (const changed of [{ rank: 2 }, { percentile: 101 }, { targetWeight: .03 }, { blocks: { ...row.blocks, target: 2 } }]) {
    const bytes = Buffer.from(JSON.stringify([{ ...row, ...changed }]));
    assert.throws(() => verifyRankingPage(bytes, { ...ranking, pages: [rankingDigest(bytes)] }, 1), /page/);
  }
  for (const changed of [{ authority: "TEST_ONLY" }, { schemaVersion: 0 }, { size: 5001 },
    { registry: { ...ranking.registry, file: "../registry.json" } }, { liveInputs: { ...ranking.liveInputs, rawFile: "file" } }]) {
    assert.throws(() => verifyRankingManifest(signRanking({ ...ranking, ...changed }), investmentKey, "owner", now), /manifest/);
  }
  assert.equal(readRankingPageNumber(undefined), 1);
  assert.equal(readRankingPageNumber("100"), 100);
  for (const input of ["0", "01", "101", "-1", "1.2", ["1", "2"]]) assert.equal(readRankingPageNumber(input), null);
});
