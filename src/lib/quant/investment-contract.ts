import { createHash, createHmac, timingSafeEqual } from "node:crypto";

export const rankingPageSize = 50;
export const rankingPageBytes = 65_536;
export const rankingManifestBytes = 32_768;
export const rankingBlocks = ["momentum", "relative_strength", "low_risk", "liquidity"] as const;
export const rankingInputs = ["governance", "window", "incidents", "calendar", "pipeline"] as const;
type Hex = string;
type JournalHead = { file: string; sha256: Hex };

export type RankingManifest = {
  schemaVersion: 1;
  authority: "RESEARCH_RANKINGS";
  ownerScope: Hex;
  modelId: string;
  modelVersion: string;
  codeSha: Hex;
  seal: Hex;
  manifest: Hex;
  gateDecision: Hex;
  registry: JournalHead;
  liveInputs: Record<typeof rankingInputs[number], Hex>;
  session: string;
  asOf: string;
  expiresAt: string;
  nextOpen: string;
  size: number;
  proxyCosts: boolean;
  pages: Hex[];
  runId: Hex;
};

export type RankingRow = {
  instrumentId: string;
  symbol: string;
  rank: number;
  percentile: number;
  advInr: number;
  volatility: number;
  blocks: Record<typeof rankingBlocks[number], number>;
};

const hash = /^[a-f0-9]{64}$/;
const sha = /^[a-f0-9]{40}$/;
const modelId = /^[A-Za-z0-9][A-Za-z0-9_.-]{0,95}$/;
const timestamp = /^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d\.\d{3}Z$/;
const instrument = /^[a-f0-9]{8}(?:-[a-f0-9]{4}){3}-[a-f0-9]{12}$/;
const manifestKeys = ["schemaVersion", "authority", "ownerScope", "modelId", "modelVersion", "codeSha", "seal",
  "manifest", "gateDecision", "registry", "liveInputs", "session", "asOf", "expiresAt", "nextOpen", "size",
  "proxyCosts", "pages", "runId"];
const rowKeys = ["instrumentId", "symbol", "rank", "percentile", "advInr", "volatility", "blocks"];

function exact(value: unknown, keys: readonly string[]): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value)
    && Object.keys(value).length === keys.length && keys.every(key => Object.hasOwn(value, key));
}

function matches(value: unknown, pattern: RegExp): value is string {
  return typeof value === "string" && pattern.test(value);
}

function instant(value: unknown) {
  if (!matches(value, timestamp)) return NaN;
  const milliseconds = Date.parse(value);
  return Number.isFinite(milliseconds) && new Date(milliseconds).toISOString() === value ? milliseconds : NaN;
}

function validDay(value: unknown): value is string {
  return typeof value === "string" && Number.isFinite(instant(value + "T00:00:00.000Z"));
}

function numberIn(value: unknown, low: number, high = Number.MAX_VALUE): value is number {
  return typeof value === "number" && Number.isFinite(value) && value >= low && value <= high;
}

export function rankingDigest(bytes: Buffer | string) {
  return createHash("sha256").update(bytes).digest("hex");
}

export function readRankingPageNumber(page: string | string[] | null | undefined) {
  if (page === undefined || page === null) return 1;
  return matches(page, /^[1-9][0-9]{0,2}$/) && Number(page) <= 100 ? Number(page) : null;
}

export function verifyRankingManifest(bytes: Buffer, key: string | undefined, owner: string | undefined, now: number) {
  if (!owner || !matches(key, hash) || bytes.length > rankingManifestBytes) throw new Error("Invalid investment envelope");
  const envelope: unknown = JSON.parse(bytes.toString("utf8"));
  if (!exact(envelope, ["payload", "sha256", "signature"]) || typeof envelope.payload !== "string"
    || !matches(envelope.sha256, hash) || !matches(envelope.signature, hash)) throw new Error("Invalid investment envelope");
  const raw = Buffer.from(envelope.payload, "base64");
  const signature = createHmac("sha256", Buffer.from(key, "hex")).update("quant/investment/v1\0").update(raw).digest();
  if (raw.toString("base64") !== envelope.payload || rankingDigest(raw) !== envelope.sha256
    || !timingSafeEqual(signature, Buffer.from(envelope.signature, "hex"))) throw new Error("Invalid investment integrity");
  const value: unknown = JSON.parse(raw.toString("utf8"));
  if (!exact(value, manifestKeys) || value.schemaVersion !== 1 || value.authority !== "RESEARCH_RANKINGS"
    || value.ownerScope !== rankingDigest(owner) || !matches(value.modelId, modelId) || !matches(value.modelVersion, modelId)
    || !matches(value.codeSha, sha) || ![value.seal, value.manifest, value.gateDecision, value.runId].every(d => matches(d, hash))
    || !exact(value.registry, ["file", "sha256"]) || !matches(value.registry.file, /^\d{8}\.json$/)
    || !matches(value.registry.sha256, hash) || !exact(value.liveInputs, rankingInputs)
    || !Object.values(value.liveInputs).every(d => matches(d, hash)) || !validDay(value.session)
    || !numberIn(value.size, 1, 5000) || !Number.isInteger(value.size) || typeof value.proxyCosts !== "boolean"
    || !Array.isArray(value.pages) || !value.pages.every(d => matches(d, hash))
    || value.pages.length !== Math.ceil(value.size / rankingPageSize)) throw new Error("Invalid investment manifest");
  const issue = instant(value.asOf);
  const expires = instant(value.expiresAt);
  const opening = instant(value.nextOpen);
  if (!(Date.parse(value.session) <= issue && issue <= now && now < expires && expires <= opening
    && expires - issue <= 30 * 60 * 1000 && opening <= Date.parse(value.session) + 15 * 86400000
    && Date.parse(value.session) < opening)) throw new Error("Investment window expired or invalid");
  return value as unknown as RankingManifest;
}

export function verifyRankingPage(bytes: Buffer, manifest: RankingManifest, page: number) {
  const offset = (page - 1) * rankingPageSize;
  const length = Math.min(manifest.size - offset, rankingPageSize);
  const digest = manifest.pages[page - 1];
  if (length < 1 || bytes.length > rankingPageBytes || !digest || rankingDigest(bytes) !== digest) {
    throw new Error("Invalid investment page integrity");
  }
  const rows: unknown = JSON.parse(bytes.toString("utf8"));
  const instruments = new Set<string>();
  if (!Array.isArray(rows) || rows.length !== length || !rows.every((row: unknown, index) => {
    if (!exact(row, rowKeys) || !matches(row.instrumentId, instrument) || instruments.has(row.instrumentId)
      || !matches(row.symbol, /^[A-Z0-9&.\-]{1,30}$/) || row.rank !== offset + index + 1
      || !numberIn(row.percentile, 0, 100) || !numberIn(row.advInr, 0) || !numberIn(row.volatility, 0)
      || !exact(row.blocks, rankingBlocks) || !Object.values(row.blocks).every(n => numberIn(n, -Number.MAX_VALUE))) return false;
    instruments.add(row.instrumentId);
    return true;
  })) throw new Error("Invalid investment page");
  return rows as RankingRow[];
}
