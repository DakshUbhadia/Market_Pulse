import assert from "node:assert/strict";
import { createHash, createHmac } from "node:crypto";
import { test } from "node:test";
import { isStatusOwner, parseStatus, syncDecision, verifyEnvelope } from "../src/lib/quant/status-contract.ts";

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

test("status is owner scoped", () => {
  assert.equal(isStatusOwner("owner", "owner"), true);
  assert.equal(isStatusOwner("reader", "owner"), false);
  assert.equal(isStatusOwner("owner", undefined), false);
  assert.equal(isStatusOwner(undefined, "owner"), false);
});

test("blocked and test-only snapshots carry status fields only", () => {
  assert.deepEqual(parseStatus(status), status);
  assert.equal(parseStatus({ ...status, authority: "TEST_ONLY" }).authority, "TEST_ONLY");
  for (const extra of [{ schemaVersion: 2 }, { recommendations: ["stock"] }, { fallback: "ADMITTED" },
    { humanReview: ["PENDING"] }, { sealHash: "f".repeat(64) }, { marketSession: "2026-11-31" }]) {
    assert.throws(() => verifyEnvelope(sign({ ...status, ...extra }), key, now), /schema/);
  }
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
