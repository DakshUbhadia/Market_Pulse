const digest = /^[a-f0-9]{64}$/;
const sha = /^[a-f0-9]{40}$/;
const version = /^[a-zA-Z0-9_.-]{1,64}$/;
const runId = /^[0-9]{8}T[0-9]{6}-[a-f0-9]{8}$/;
const uuid = /^[a-f0-9]{8}(?:-[a-f0-9]{4}){3}-[a-f0-9]{12}$/;

export const artifactClasses = {
  current: "ARCHIVED_INPUT", acceptance: "LOCAL_TEST", certificate: "CERTIFIED_SOFTWARE",
  refresh: "ARCHIVED_INPUT", smoke: "LOCAL_TEST", pilot: "ARCHIVED_INPUT", filing: "ARCHIVED_INPUT",
  ceiling: "ARCHIVED_INPUT", discovery: "ARCHIVED_INPUT", shares: "ARCHIVED_INPUT", joint: "ARCHIVED_INPUT",
  interval: "ARCHIVED_INPUT", capital: "ARCHIVED_INPUT", tidewater: "ARCHIVED_INPUT", fallback: "ARCHIVED_INPUT",
  cairn: "DIAGNOSTIC", runs: "DIAGNOSTIC", controlled: "DIAGNOSTIC", forward: "TEST_ONLY", monitoring: "TEST_ONLY",
  capitalQueue: "ARCHIVED_INPUT", riskPolicy: "CONFIGURED_POLICY", priorSmoke: "LOCAL_TEST",
} as const;

const metricSources = {
  localTestsPassed: "acceptance", livePassed: "acceptance", liveFailed: "acceptance", restoredFiles: "acceptance",
  discoveryCells: "discovery", discoveryInstruments: "discovery", usabilityCells: "ceiling", capitalCandidates: "capital",
  pilotCells: "pilot", admittedDocuments: "pilot", verifiedRepairs: "pilot",
  priorLivePassed: "priorSmoke", priorLiveFailed: "priorSmoke", realCohorts: "current", testSignals: "forward",
  shadowObservations: "forward", matured21: "forward", matured63: "forward", testIncidents: "monitoring", realIncidents: "current",
} as const;

type Artifact = keyof typeof artifactClasses;
type Metric = keyof typeof metricSources;
type StructuralRun = { id: string; basis: "PRICE" | "TOTAL_RETURN"; start: string | null; end: string | null;
  codeSha: string | null; manifest: string | null; outcomeHash: string | null };

export type ResearchDetails = {
  artifacts: Partial<Record<Artifact, { sha256: string; evidenceClass: typeof artifactClasses[Artifact] }>>;
  metrics: Partial<Record<Metric, { value: number; artifact: Artifact; asOf: string | null }>>;
  jointCounts: { cutoff: string; complete: number; eligible: number; topComplete: number; topEligible: number; valueMissing: number | null }[];
  probes: { route: string; asOf: string | null; httpStatus: number | null; state: "BLOCKED" | "UNASSESSED" }[];
  filingQueue: { symbol: string; cutoff: string; period: string | null; knownBy: string | null; candidate: boolean; top100: boolean }[];
  capitalQueue: { id: string; instrument: string; event: string; state: string; effective: string | null;
    known: string | null; source: string | null; lineage: boolean; missing: string[] }[];
  runs: StructuralRun[];
  riskPolicy: Record<typeof policyKeys[number], number>;
  fallbackStart: string | null;
  tidewaterAudit: string | null;
  tidewaterExhausted: boolean;
  cairnObserved: string | null;
  fourArmDiagnostic: boolean;
  continuousJoint: boolean;
  eod: "BLOCKED" | "UNASSESSED";
  scheduler: "ACCESS_DENIED" | "UNASSESSED";
  certifiedSha: string | null;
  riskVersion: string | null;
  accountingVersion: string | null;
};

const policyKeys = ["max_weight", "max_cluster_weight", "adv_fraction", "target_volatility", "gross_exposure", "turnover_penalty"] as const;
const detailKeys = ["artifacts", "metrics", "jointCounts", "probes", "filingQueue", "capitalQueue", "runs", "riskPolicy",
  "fallbackStart", "tidewaterAudit", "tidewaterExhausted", "cairnObserved", "fourArmDiagnostic", "continuousJoint",
  "eod", "scheduler", "certifiedSha", "riskVersion", "accountingVersion"];
const capitalStates = new Set(["CANDIDATE", "TERMS_VERIFIED", "DATES_VERIFIED", "VERIFIED_COMPLETE", "REJECTED", "NEEDS_REVIEW", "UNASSESSED"]);
const facts = new Set(["announced_at", "credit_date", "effective_date", "event_type", "instrument_id", "known_at",
  "listing_date", "record_date", "security_lineage_id", "share_multiplier", "source_bytes", "valid_dates",
  "shares_added", "shares_removed", "paid_up_capital_before", "paid_up_capital_after", "face_value_before", "face_value_after"]);

function record(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function fields(value: unknown, keys: readonly string[]): value is Record<string, unknown> {
  return record(value) && Object.keys(value).length === keys.length && keys.every(key => Object.hasOwn(value, key));
}

function match(value: unknown, pattern: RegExp) {
  return typeof value === "string" && pattern.test(value);
}

function dateTime(value: unknown) {
  if (typeof value !== "string" || !Number.isFinite(Date.parse(value))) return false;
  const canonical = new Date(value).toISOString();
  return value === canonical || value === canonical.slice(0, 10);
}

function optional(value: unknown, valid: (value: unknown) => boolean) {
  return value === null || valid(value);
}

function date(value: unknown) {
  return typeof value === "string" && value.length === 10 && dateTime(value);
}

function numeric(value: unknown): value is number {
  return typeof value === "number" && Number.isSafeInteger(value) && value >= 0;
}

function rows(value: unknown, limit: number, validate: (value: unknown) => boolean) {
  return Array.isArray(value) && value.length <= limit && value.every(validate);
}

export function parseResearchDetails(value: unknown): ResearchDetails {
  if (!fields(value, detailKeys) || !record(value.artifacts) || !record(value.metrics)
    || !Object.hasOwn(value.artifacts, "current")) throw new Error("Invalid quant research schema");
  for (const [key, entry] of Object.entries(value.artifacts)) {
    if (!Object.hasOwn(artifactClasses, key) || !fields(entry, ["sha256", "evidenceClass"])
      || !match(entry.sha256, digest) || entry.evidenceClass !== artifactClasses[key as Artifact]) {
      throw new Error("Invalid quant artifact schema");
    }
  }
  for (const [key, entry] of Object.entries(value.metrics)) {
    if (!Object.hasOwn(metricSources, key) || !fields(entry, ["value", "artifact", "asOf"])
      || !numeric(entry.value) || !optional(entry.asOf, dateTime) || typeof entry.artifact !== "string"
      || !Object.hasOwn(value.artifacts, entry.artifact)
      || (entry.artifact !== metricSources[key as Metric]
        && !(entry.artifact === "current" && ["discoveryCells", "discoveryInstruments", "usabilityCells", "capitalCandidates"].includes(key)))) {
      throw new Error("Invalid quant metric schema");
    }
  }
  if (!rows(value.jointCounts, 120, row => fields(row, ["cutoff", "complete", "eligible", "topComplete", "topEligible", "valueMissing"])
    && date(row.cutoff) && numeric(row.complete) && numeric(row.eligible) && row.complete <= row.eligible
    && numeric(row.topComplete) && numeric(row.topEligible) && row.topComplete <= row.topEligible && row.topEligible <= 100
    && (row.valueMissing === null || numeric(row.valueMissing) && row.valueMissing <= row.eligible))
    || !rows(value.probes, 16, row => fields(row, ["route", "asOf", "httpStatus", "state"])
      && match(row.route, /^[a-z0-9.-]{1,80}$/) && optional(row.asOf, dateTime)
      && optional(row.httpStatus, n => numeric(n) && n >= 100 && n <= 599)
      && (row.state === "BLOCKED" || row.state === "UNASSESSED"))
    || !rows(value.filingQueue, 80, row => fields(row, ["symbol", "cutoff", "period", "knownBy", "candidate", "top100"])
      && match(row.symbol, /^[A-Z0-9&.-]{1,30}$/) && date(row.cutoff) && optional(row.period, date)
      && optional(row.knownBy, dateTime) && typeof row.candidate === "boolean" && typeof row.top100 === "boolean")
    || !rows(value.capitalQueue, 80, row => fields(row, ["id", "instrument", "event", "state", "effective", "known", "source", "lineage", "missing"])
      && match(row.id, digest) && match(row.instrument, uuid) && match(row.event, /^[A-Z_]{1,40}$/)
      && typeof row.state === "string" && capitalStates.has(row.state) && optional(row.effective, date)
      && optional(row.known, dateTime) && optional(row.source, s => match(s, digest))
      && typeof row.lineage === "boolean" && rows(row.missing, facts.size, fact => typeof fact === "string" && facts.has(fact)))
    || !rows(value.runs, 20, row => fields(row, ["id", "basis", "start", "end", "codeSha", "manifest", "outcomeHash"])
      && match(row.id, runId) && (row.basis === "PRICE" || row.basis === "TOTAL_RETURN")
      && optional(row.start, date) && optional(row.end, date) && optional(row.codeSha, s => match(s, sha))
      && optional(row.manifest, s => match(s, digest)) && optional(row.outcomeHash, s => match(s, digest)))
    || !fields(value.riskPolicy, policyKeys) || !Object.values(value.riskPolicy).every(n => typeof n === "number" && Number.isFinite(n) && n >= 0 && n <= 1)
    || !optional(value.fallbackStart, date) || !optional(value.tidewaterAudit, s => match(s, digest))
    || !optional(value.cairnObserved, date) || !optional(value.certifiedSha, s => match(s, sha))
    || !optional(value.riskVersion, s => match(s, version)) || !optional(value.accountingVersion, s => match(s, version))
    || ![value.tidewaterExhausted, value.fourArmDiagnostic, value.continuousJoint].every(v => typeof v === "boolean")
    || (value.eod !== "BLOCKED" && value.eod !== "UNASSESSED")
    || (value.scheduler !== "ACCESS_DENIED" && value.scheduler !== "UNASSESSED")) {
    throw new Error("Invalid quant research schema");
  }
  return value as unknown as ResearchDetails;
}
