import { getMultipleStockQuotesRealtime } from "@/lib/actions/finnhub.actions";
import { NextResponse } from "next/server";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";
export const revalidate = 0;

export async function GET(req: Request): Promise<Response> {
  const url = new URL(req.url);
  const symbol = url.searchParams.get("symbol");
  const exchange = url.searchParams.get("exchange") || "US";

  if (!symbol) {
    return NextResponse.json({ error: "Missing symbol" }, { status: 400 });
  }

  try {
    const quotes = await getMultipleStockQuotesRealtime({
      requests: [{ symbol: symbol.toUpperCase(), exchange }],
      includeMetrics: false,
    });

    if (quotes.length === 0) {
      return NextResponse.json({ error: "Quote not found" }, { status: 404 });
    }

    const quote = quotes[0];

    return NextResponse.json({
      symbol: quote.symbol,
      name: quote.name || symbol,
      company: quote.name || symbol,
      exchange: quote.exchange || exchange,
      currentPrice: quote.currentPrice ?? 0,
      change: quote.change ?? 0,
      changePercent: quote.percentChange ?? 0,
      openPrice: quote.openPrice,
      highPrice: quote.highPrice,
      lowPrice: quote.lowPrice,
    });
  } catch (error) {
    console.error("Quote info error:", error);
    return NextResponse.json(
      { error: "Failed to fetch quote" },
      { status: 500 }
    );
  }
}
