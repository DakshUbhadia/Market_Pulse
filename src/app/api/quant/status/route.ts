import { canReadQuantStatus, privateStatusHeaders, readQuantStatus } from "@/lib/quant/status-server";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function GET() {
  if (!await canReadQuantStatus()) {
    return Response.json({ error: "Forbidden" }, { status: 403, headers: privateStatusHeaders });
  }
  return Response.json(await readQuantStatus(), { headers: privateStatusHeaders });
}
