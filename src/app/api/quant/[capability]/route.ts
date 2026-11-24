import { readRankingPageNumber } from "@/lib/quant/investment-contract";
import { investmentCapabilities, readOwnerInvestment } from "@/lib/quant/investment-server";
import { canReadQuantStatus, privateStatusHeaders } from "@/lib/quant/status-server";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

type Context = { params: Promise<{ capability: string }> };

async function capabilityFor({ params }: Context) {
  const { capability } = await params;
  return investmentCapabilities.find(entry => entry === capability);
}

export async function HEAD(_request: Request, context: Context) {
  const permitted = await canReadQuantStatus();
  const status = permitted ? (await capabilityFor(context) ? 204 : 404) : 403;
  return new Response(null, { status, headers: privateStatusHeaders });
}

export async function GET(request: Request, context: Context) {
  const headers = privateStatusHeaders;
  if (!await canReadQuantStatus()) return Response.json({ error: "Forbidden" }, { status: 403, headers });
  const capability = await capabilityFor(context);
  if (!capability) return Response.json({ error: "Not found" }, { status: 404, headers });
  const params = new URL(request.url).searchParams;
  const page = readRankingPageNumber(params.get("page"));
  if (page === null || params.getAll("page").length > 1) {
    return Response.json({ error: "Invalid page" }, { status: 400, headers });
  }
  const result = await readOwnerInvestment(capability, page);
  return Response.json(result, { status: result.state === "PAGE_NOT_FOUND" ? 404 : 200, headers });
}
