import { MAX_STATUS_BYTES, verifyEnvelope } from "@/lib/quant/status-contract";
import { canSyncQuantStatus, privateStatusHeaders, quantStatusSyncEnabled, storeQuantStatus } from "@/lib/quant/status-server";

export const runtime = "nodejs";

export async function POST(request: Request) {
  if (!quantStatusSyncEnabled()) return reply("DISABLED", 404);
  if (!canSyncQuantStatus(request.headers.get("authorization"))) return reply("FORBIDDEN", 403);
  if (request.headers.get("content-type")?.split(";")[0].trim() !== "application/json") {
    return reply("UNSUPPORTED_MEDIA_TYPE", 415);
  }
  if (!request.body) return reply("INVALID", 400);
  const reader = request.body.getReader();
  const parts: Uint8Array[] = [];
  let size = 0;
  let next;
  try {
    for (;;) {
      const { done, value } = await reader.read();
      if (done) break;
      size += value.length;
      if (size > MAX_STATUS_BYTES) {
        await reader.cancel();
        return reply("TOO_LARGE", 413);
      }
      parts.push(value);
    }
    next = verifyEnvelope(JSON.parse(Buffer.concat(parts).toString("utf8")), process.env.QUANT_STATUS_SIGNING_KEY);
  } catch {
    return reply("INVALID", 400);
  } finally {
    reader.releaseLock();
  }
  if (next.stale) return reply("STALE", 409);
  if (next.status.authority !== "STATUS_ONLY") return reply("FORBIDDEN", 403);
  try {
    const result = await storeQuantStatus(next);
    return reply(result, { ACCEPT: 201, DUPLICATE: 200, REPLAY: 409, CONTENDED: 503 }[result]);
  } catch {
    return reply("UNAVAILABLE", 503);
  }
}

function reply(state: string, status: number) {
  return Response.json({ state }, { status, headers: privateStatusHeaders });
}
