import { createHash, createHmac, timingSafeEqual } from "node:crypto";

export const MAX_STATUS_BYTES = 65_536;
export const MAX_STATUS_AGE_MS = 48 * 60 * 60 * 1000;

export type CoverageRow = {
  cutoff: string;
  filing: number | null;
  filingTop100: number | null;
  ceiling: number | null;
  ceilingTop100: number | null;
  shares: number | null;
  sharesTop100: number | null;
  joint: number | null;
  jointTop100: number | null;
};

export type QuantStatus = {
  schemaVersion: 1;
  runId: string;
  gitCommit: string;
  asOf: string;
  marketSession: string | null;
  authority: "STATUS_ONLY" | "TEST_ONLY";
  validationStatus: "BLOCKED" | "UNASSESSED";
  archiveReadiness: "READY" | "NOT_READY" | "UNASSESSED";
  filingSources: "SOURCE_LIMITED" | "UNASSESSED";
  jointMatrix: "THRESHOLDS_MET" | "BLOCKED" | "UNASSESSED";
  humanReview: "PENDING" | "RESOLVED" | "UNASSESSED";
  fallback: "ADMITTED" | "NOT_ADMITTED" | "UNASSESSED";
  implementation: "CERTIFIED" | "UNVERIFIED";
  v1Version: string;
  v2Version: string;
  featureVersion: string;
  costVersion: string;
  evidenceVersion: string;
  sealHash: null;
  inputManifestHash: string | null;
  openIncidents: number | null;
  discoveryGaps: number | null;
  capitalCandidates: number | null;
  coverage: CoverageRow[];
};

export type Envelope = { payload: string; sha256: string; signature: string };
type ObjectRecord = Record<string, unknown>;

const hash = /^[a-f0-9]{64}$/;
const version = /^[a-zA-Z0-9_.-]{1,64}$/;
const statusKeys = [
  "schemaVersion", "runId", "gitCommit", "asOf", "marketSession", "authority", "validationStatus",
  "archiveReadiness", "filingSources", "jointMatrix",
  "humanReview", "fallback", "implementation", "v1Version", "v2Version", "featureVersion", "costVersion",
  "evidenceVersion", "sealHash", "inputManifestHash", "openIncidents", "discoveryGaps", "capitalCandidates", "coverage",
];
const coverageKeys = [
  "cutoff", "filing", "filingTop100", "ceiling", "ceilingTop100", "shares", "sharesTop100", "joint", "jointTop100",
] as const;

function exact(value: unknown, keys: readonly string[]): value is ObjectRecord {
  return typeof value === "object" && value !== null && !Array.isArray(value)
    && Object.keys(value).length === keys.length && keys.every(key => Object.hasOwn(value, key));
}

function matches(value: unknown, pattern: RegExp): value is string {
  return typeof value === "string" && pattern.test(value);
}

function date(value: unknown): value is string {
  if (!matches(value, /^\d{4}-\d{2}-\d{2}$/)) return false;
  const parsed = new Date(value);
  return Number.isFinite(parsed.getTime()) && parsed.toISOString().slice(0, 10) === value;
}

function count(value: unknown) {
  return value === null || (typeof value === "number" && Number.isSafeInteger(value) && value >= 0);
}

export function parseStatus(value: unknown): QuantStatus {
  if (!exact(value, statusKeys) || value.schemaVersion !== 1 || !matches(value.runId, hash)
    || !matches(value.gitCommit, /^[a-f0-9]{40}$/)
    || !matches(value.asOf, /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$/)
    || !Number.isFinite(Date.parse(value.asOf)) || new Date(value.asOf).toISOString() !== value.asOf
    || (value.marketSession !== null && (!date(value.marketSession) || value.marketSession > value.asOf.slice(0, 10)))
    || (value.authority !== "STATUS_ONLY" && value.authority !== "TEST_ONLY")
    || (value.validationStatus !== "BLOCKED" && value.validationStatus !== "UNASSESSED")
    || !matches(value.archiveReadiness, /^(READY|NOT_READY|UNASSESSED)$/)
    || !matches(value.filingSources, /^(SOURCE_LIMITED|UNASSESSED)$/)
    || !matches(value.jointMatrix, /^(THRESHOLDS_MET|BLOCKED|UNASSESSED)$/)
    || !matches(value.humanReview, /^(PENDING|RESOLVED|UNASSESSED)$/)
    || !matches(value.fallback, /^(ADMITTED|NOT_ADMITTED|UNASSESSED)$/)
    || !matches(value.implementation, /^(CERTIFIED|UNVERIFIED)$/)
    || (value.humanReview !== "RESOLVED" && value.fallback === "ADMITTED")
    || ![value.v1Version, value.v2Version, value.featureVersion, value.costVersion, value.evidenceVersion].every(v => matches(v, version))
    || value.sealHash !== null || (value.inputManifestHash !== null && !matches(value.inputManifestHash, hash))
    || ![value.openIncidents, value.discoveryGaps, value.capitalCandidates].every(count)
    || !Array.isArray(value.coverage) || value.coverage.length > 120) {
    throw new Error("Invalid quant status schema");
  }
  let previous = "";
  for (const row of value.coverage) {
    if (!exact(row, coverageKeys) || !date(row.cutoff) || row.cutoff <= previous || row.cutoff > value.asOf.slice(0, 10)
      || coverageKeys.slice(1).some(key => row[key] !== null
        && (typeof row[key] !== "number" || !Number.isFinite(row[key]) || row[key] < 0 || row[key] > 100))) {
      throw new Error("Invalid quant coverage row");
    }
    previous = row.cutoff;
  }
  return value as unknown as QuantStatus;
}

export function verifyEnvelope(value: unknown, key: string | undefined, now = Date.now()) {
  if (!key || !hash.test(key) || !exact(value, ["payload", "sha256", "signature"])
    || typeof value.payload !== "string" || value.payload.length > MAX_STATUS_BYTES
    || !matches(value.sha256, hash) || !matches(value.signature, hash)) {
    throw new Error("Invalid quant status envelope");
  }
  const bytes = Buffer.from(value.payload, "base64");
  const digest = createHash("sha256").update(bytes).digest("hex");
  const signature = createHmac("sha256", Buffer.from(key, "hex")).update(bytes).digest();
  if (bytes.toString("base64") !== value.payload || digest !== value.sha256
    || !timingSafeEqual(signature, Buffer.from(value.signature, "hex"))) {
    throw new Error("Quant status integrity check failed");
  }
  const status = parseStatus(JSON.parse(bytes.toString("utf8")));
  const age = now - Date.parse(status.asOf);
  if (age < -300_000) throw new Error("Quant status timestamp is in the future");
  return { envelope: value as Envelope, status, stale: age > MAX_STATUS_AGE_MS };
}

export function isStatusOwner(userId: string | undefined, ownerId: string | undefined) {
  return Boolean(userId && ownerId && userId === ownerId);
}

export function syncDecision(current: { sha256: string; asOf: string } | null, next: { sha256: string; asOf: string }) {
  if (current?.sha256 === next.sha256) return "DUPLICATE";
  if (current && next.asOf <= current.asOf) return "REPLAY";
  return "ACCEPT";
}
