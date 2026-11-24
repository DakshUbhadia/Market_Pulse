import { open } from "node:fs/promises";
import { timingSafeEqual } from "node:crypto";
import { MongoClient, MongoServerError, type Collection } from "mongodb";
import { requireCurrentUser } from "@/lib/actions/session.actions";
import { type Envelope, isStatusOwner, MAX_STATUS_BYTES, syncDecision, verifyEnvelope } from "./status-contract";

type StoredStatus = { _id: "current"; envelope: Envelope; sha256: string; asOf: string };
let connection: MongoClient | undefined;

export const privateStatusHeaders = { "Cache-Control": "private, no-store" };

export async function canReadQuantStatus() {
  const ownerId = process.env.QUANT_STATUS_OWNER_ID;
  if (!ownerId) return false;
  try {
    const user = await requireCurrentUser();
    return isStatusOwner(user.userId, ownerId);
  } catch {
    return false;
  }
}

function collection(): Collection<StoredStatus> {
  const uri = process.env.QUANT_STATUS_MONGODB_URI;
  const database = process.env.QUANT_STATUS_MONGODB_DB;
  if (!uri || !database) throw new Error("Status storage unavailable");
  connection ??= new MongoClient(uri, { serverSelectionTimeoutMS: 5_000 });
  return connection.db(database).collection<StoredStatus>("quant_status");
}

export function quantStatusSyncEnabled() {
  return process.env.QUANT_STATUS_SYNC === "true";
}

export function canSyncQuantStatus(authorization: string | null) {
  const secret = process.env.QUANT_STATUS_SYNC_TOKEN;
  if (!secret || !/^[a-f0-9]{64}$/.test(secret) || !authorization?.startsWith("Bearer ")) return false;
  const bytes = Buffer.from(authorization.slice(7));
  const expected = Buffer.from(secret);
  return bytes.length === expected.length && timingSafeEqual(bytes, expected);
}

async function readEnvelope(file: string) {
  const handle = await open(file);
  try {
    const buffer = Buffer.alloc(MAX_STATUS_BYTES + 1);
    let offset = 0;
    while (offset < buffer.length) {
      const { bytesRead } = await handle.read(buffer, offset, buffer.length - offset);
      if (!bytesRead) break;
      offset += bytesRead;
    }
    if (offset > MAX_STATUS_BYTES) throw new Error("Invalid quant envelope size");
    return JSON.parse(buffer.subarray(0, offset).toString("utf8")) as unknown;
  } finally {
    await handle.close();
  }
}

function verifyStoredEnvelope(envelope: unknown) {
  return verifyEnvelope(envelope, process.env.QUANT_STATUS_SIGNING_KEY, Date.now(),
    process.env.QUANT_STATUS_OWNER_ID, process.env.QUANT_STATUS_PREVIOUS_SIGNING_KEY);
}

async function readLocalStatus(file: string) {
  // The publisher commits this checkpoint before replacing the display pointer.
  const checkpoint = await readEnvelope(file + ".latest").catch((error: NodeJS.ErrnoException) => {
    if (error.code === "ENOENT") return null;
    throw error;
  });
  if (checkpoint === null) return verifyStoredEnvelope(await readEnvelope(file));
  const archived = verifyStoredEnvelope(checkpoint);
  const pointer = await readEnvelope(file).then(verifyStoredEnvelope).catch(() => null);
  return pointer?.envelope.sha256 === archived.envelope.sha256 ? pointer : { ...archived, stale: true };
}

export async function readQuantStatus() {
  const file = process.env.QUANT_STATUS_FILE;
  try {
    const local = file && !process.env.VERCEL;
    if (!local && !quantStatusSyncEnabled()) {
      return { state: process.env.VERCEL ? "HOSTED_EMPTY" : "EMPTY" } as const;
    }
    const stored = local ? null : await collection().findOne({ _id: "current" });
    if (!local && !stored) return { state: "HOSTED_EMPTY" } as const;
    const { status, stale } = local ? await readLocalStatus(file) : verifyStoredEnvelope(stored?.envelope);
    return { state: stale ? "STALE" : "AVAILABLE", status } as const;
  } catch (error) {
    return { state: (error as NodeJS.ErrnoException).code === "ENOENT" ? "EMPTY" : "INVALID" } as const;
  }
}

export async function storeQuantStatus(next: ReturnType<typeof verifyEnvelope>) {
  const store = collection();
  const record: StoredStatus = { _id: "current", envelope: next.envelope,
    sha256: next.envelope.sha256, asOf: next.status.asOf };
  for (let attempt = 0; attempt < 3; attempt++) {
    const current = await store.findOne({ _id: "current" }, { projection: { sha256: 1, asOf: 1 } });
    const decision = syncDecision(current, record);
    if (decision !== "ACCEPT") return decision;
    try {
      if (!current) {
        await store.insertOne(record);
        return "ACCEPT";
      }
      const result = await store.replaceOne({ _id: "current", sha256: current.sha256 }, record);
      if (result.modifiedCount === 1) return "ACCEPT";
    } catch (error) {
      if (!(error instanceof MongoServerError) || error.code !== 11000) throw error;
    }
  }
  return "CONTENDED";
}
