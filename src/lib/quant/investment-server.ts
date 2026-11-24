import { isAbsolute, resolve } from "node:path";
import { readQuantStatus } from "./status-server";
import { rankingDigest, rankingManifestBytes, rankingPageBytes, verifyRankingManifest, verifyRankingPage } from "./investment-contract";
import type { RankingManifest } from "./investment-contract";

export const investmentCapabilities = ["rankings", "forward", "portfolio"] as const;
type Capability = typeof investmentCapabilities[number];
type Inputs = RankingManifest["liveInputs"];
type StatusRead = Awaited<ReturnType<typeof readQuantStatus>>;

function locked(...reasons: string[]) {
  return { state: "LOCKED", reasons } as const;
}

async function boundedRead(file: string, max: number) {
  const fs = process.getBuiltinModule("node:fs/promises")!;
  const handle = await fs.open(file, "r");
  try {
    const buffer = Buffer.alloc(max + 1);
    let offset = 0;
    while (offset < buffer.length) {
      const result = await handle.read(buffer, offset, buffer.length - offset);
      if (!result.bytesRead) break;
      offset += result.bytesRead;
    }
    if (offset > max) throw new Error("Investment artifact exceeds its byte limit");
    return buffer.subarray(0, offset);
  } finally {
    await handle.close();
  }
}

async function latestFile(dir: string, pattern: RegExp) {
  const fs = process.getBuiltinModule("node:fs/promises")!;
  const names = await fs.readdir(dir).catch((error: NodeJS.ErrnoException) => {
    if (error.code === "ENOENT") return [];
    throw error;
  });
  return names.filter(name => pattern.test(name)).sort().at(-1);
}

async function headDigest(dir: string, fallback?: string) {
  const file = await latestFile(dir, /^\d{8}\.json$/);
  const path = file ? resolve(dir, file) : fallback;
  if (!path) throw new Error("Missing investment journal");
  return { file, sha256: rankingDigest(await boundedRead(path, 1_048_576)) };
}

async function liveInputs(dataRoot: string): Promise<Inputs> {
  const fileDigest = async (path: string) => rankingDigest(await boundedRead(resolve(dataRoot, path), 1_048_576));
  const [governance, incidents, window, calendar, pipeline] = await Promise.all([
    headDigest(resolve(dataRoot, "research/governance/events")),
    headDigest(resolve(dataRoot, "research/incidents/events"), resolve(dataRoot, "research/incidents/ledger.json")),
    fileDigest("reports/v1-evaluation-window-admitted.json"), fileDigest("reports/calendar-health.json"),
    fileDigest("state/pipeline_state.json"),
  ]);
  return { governance: governance.sha256, incidents: incidents.sha256, window, calendar, pipeline };
}

function statusBlockers(result: StatusRead) {
  if (result.state !== "AVAILABLE" || result.status.authority !== "STATUS_ONLY" || result.status.schemaVersion !== 2) {
    return ["EOD_STALE", "NO_HISTORICAL_PASS"];
  }
  const status = result.status;
  return [
    ...(status.humanReview === "RESOLVED" ? [] : ["GOVERNANCE_PENDING"]),
    ...(status.fallback === "ADMITTED" ? [] : ["WINDOW_NOT_ADMITTED"]),
    ...(status.implementation === "CERTIFIED" ? [] : ["SOFTWARE_UNCERTIFIED"]),
    ...(status.archiveReadiness === "READY" && status.details.eod !== "BLOCKED" && status.marketSession ? [] : ["EOD_STALE"]),
  ];
}

// Call only after the route or console has verified the current Better Auth owner.
export async function readOwnerInvestment(capability: Capability, page: number, status?: StatusRead) {
  const result = status ?? await readQuantStatus();
  const reasons = statusBlockers(result);
  if (capability === "forward") return locked(...reasons, "COHORT_NOT_ADMITTED");
  if (capability === "portfolio") {
    return locked(...reasons, "FORWARD_SAMPLE_INSUFFICIENT", "COST_POLICY_UNVERIFIED", "PUBLISH_DISABLED");
  }
  if (reasons.length) return locked(...new Set([...reasons, "NO_HISTORICAL_PASS"]));
  const key = process.env.QUANT_INVESTMENT_SIGNING_KEY;
  const projection = process.env.QUANT_INVESTMENT_FILE;
  const registry = process.env.QUANT_INVESTMENT_REGISTRY_EVENTS;
  const dataRoot = process.env.QUANT_INVESTMENT_DATA_DIR;
  if (process.env.VERCEL || process.env.QUANT_PRIVATE_RESEARCH_VIEW !== "true" || !key
    || [process.env.QUANT_STATUS_SIGNING_KEY, process.env.QUANT_STATUS_PREVIOUS_SIGNING_KEY].includes(key)
    || !projection || !registry || !dataRoot || ![projection, registry, dataRoot].every(isAbsolute)) {
    return locked("NO_HISTORICAL_PASS", "PUBLISH_DISABLED");
  }
  try {
    const [pointer, checkpoint] = await Promise.all([boundedRead(projection, rankingManifestBytes),
      boundedRead(projection + ".latest", rankingManifestBytes)]);
    if (!pointer.equals(checkpoint)) return locked("EOD_STALE");
    const manifest = verifyRankingManifest(pointer, key, process.env.QUANT_STATUS_OWNER_ID, Date.now());
    if (result.state !== "AVAILABLE" || result.status.schemaVersion !== 2
      || result.status.marketSession !== manifest.session || result.status.gitCommit !== manifest.codeSha
      || result.status.details.certifiedSha !== manifest.codeSha || result.status.v1Version !== manifest.modelVersion) {
      return locked("EOD_STALE", "SOFTWARE_UNCERTIFIED");
    }
    const archive = projection + ".history";
    const expected = manifest.asOf.replace(/[-:.]/g, "") + "-" + manifest.runId + ".json";
    const [head, inputs, historyHead] = await Promise.all([headDigest(registry), liveInputs(dataRoot),
      latestFile(archive, /^\d{8}T\d{9}Z-[a-f0-9]{64}\.json$/)]);
    if (historyHead !== expected || !(await boundedRead(resolve(archive, expected), rankingManifestBytes)).equals(pointer)) {
      return locked("EOD_STALE");
    }
    if (head.file !== manifest.registry.file || head.sha256 !== manifest.registry.sha256) return locked("NO_HISTORICAL_PASS");
    if (inputs.governance !== manifest.liveInputs.governance) return locked("GOVERNANCE_PENDING");
    if (inputs.window !== manifest.liveInputs.window) return locked("WINDOW_NOT_ADMITTED");
    if (inputs.incidents !== manifest.liveInputs.incidents) return locked("INCIDENT_OPEN");
    if (inputs.calendar !== manifest.liveInputs.calendar || inputs.pipeline !== manifest.liveInputs.pipeline) return locked("EOD_STALE");
    if (page > manifest.pages.length) return { state: "PAGE_NOT_FOUND" } as const;
    const bytes = await boundedRead(resolve(projection + ".pages", manifest.runId, (page - 1) + ".json"), rankingPageBytes);
    const rows = verifyRankingPage(bytes, manifest, page);
    if (Date.now() >= Date.parse(manifest.expiresAt)) return locked("EOD_STALE");
    return { state: "AVAILABLE", authority: manifest.authority, runId: manifest.runId, model: manifest.modelId,
      modelVersion: manifest.modelVersion, session: manifest.session, asOf: manifest.asOf, nextOpen: manifest.nextOpen,
      proxyCosts: manifest.proxyCosts, size: manifest.size, page, pageCount: manifest.pages.length, rows } as const;
  } catch {
    return locked("NO_HISTORICAL_PASS", "EOD_STALE");
  }
}
