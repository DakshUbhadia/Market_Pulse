import { getMultipleStockQuotesRealtime } from "@/lib/actions/finnhub.actions";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";
export const revalidate = 0;

type StreamQuoteRequest = {
  symbol: string;
  exchange?: string;
};

const parseItemsParam = (itemsRaw: string | null): StreamQuoteRequest[] => {
  if (!itemsRaw) return [];

  try {
    const parsed = JSON.parse(itemsRaw) as unknown;
    if (!Array.isArray(parsed)) return [];

    const items: StreamQuoteRequest[] = [];
    for (const entry of parsed) {
      if (!entry || typeof entry !== "object") continue;
      const e = entry as Partial<StreamQuoteRequest>;
      if (typeof e.symbol !== "string" || !e.symbol.trim()) continue;

      const symbol = e.symbol.trim().toUpperCase();
      const exchange = typeof e.exchange === "string" && e.exchange.trim() ? e.exchange.trim().toUpperCase() : undefined;

      items.push({ symbol, exchange });
    }

    // De-dupe by symbol+exchange while preserving order.
    const seen = new Set<string>();
    return items.filter((i) => {
      const key = `${i.symbol}::${i.exchange ?? ""}`;
      if (seen.has(key)) return false;
      seen.add(key);
      return true;
    });
  } catch {
    return [];
  }
};

const sseEvent = (args: { event?: string; data: unknown }) => {
  const payload = JSON.stringify(args.data);
  const ev = args.event ? `event: ${args.event}\n` : "";
  return `${ev}data: ${payload}\n\n`;
};

export async function GET(req: Request): Promise<Response> {
  const url = new URL(req.url);
  const items = parseItemsParam(url.searchParams.get("items"));

  if (items.length === 0) {
    return new Response("Missing or invalid 'items' query param", { status: 400 });
  }

  // Keep this conservative to avoid runaway server load.
  if (items.length > 50) {
    return new Response("Too many symbols requested (max 50)", { status: 413 });
  }

  const encoder = new TextEncoder();

  const stream = new ReadableStream<Uint8Array>({
    start(controller) {
      let closed = false;

      // Price updates can be frequent; P/E updates are heavier.
      // Auto-scale price interval with list size to reduce Finnhub rate-limit pressure.
      const basePriceIntervalMs = 10_000;
      const scaledPriceIntervalMs = Math.max(basePriceIntervalMs, items.length * 1500);
      let priceIntervalMs = scaledPriceIntervalMs;

      const peIntervalMs = 5 * 60_000;
      let lastPeRefreshAt = 0;
      const peBySymbol = new Map<string, number>();

      const write = (chunk: string) => {
        if (closed) return;
        controller.enqueue(encoder.encode(chunk));
      };

      const safeClose = () => {
        if (closed) return;
        closed = true;
        try {
          controller.close();
        } catch {
          // ignore
        }
      };

      const sendQuotes = async (opts?: { includeMetrics?: boolean }) => {
        try {
          const includeMetrics = opts?.includeMetrics === true;
          const quotes = await getMultipleStockQuotesRealtime({
            requests: items,
            includeMetrics,
          });

          // Persist last-known-good P/E so we can send it with frequent price ticks.
          if (includeMetrics) {
            for (const q of quotes) {
              if (typeof q?.symbol === "string" && Number.isFinite(q.peRatio) && q.peRatio > 0) {
                peBySymbol.set(q.symbol.toUpperCase(), q.peRatio);
              }
            }
            lastPeRefreshAt = Date.now();
          }

          const merged = quotes.map((q) => {
            const pe = peBySymbol.get(q.symbol.toUpperCase());
            return {
              ...q,
              peRatio: Number.isFinite(pe) && (pe as number) > 0 ? (pe as number) : q.peRatio,
            };
          });

          write(
            sseEvent({
              event: "quotes",
              data: {
                quotes: merged,
                at: Date.now(),
                meta: {
                  priceIntervalMs,
                  peIntervalMs,
                  peLastUpdatedAt: lastPeRefreshAt || null,
                },
              },
            })
          );
        } catch (error) {
          const message = error instanceof Error ? error.message : "Unknown error";

          // If we got rate limited, back off for this connection.
          if (typeof message === "string" && (message.includes("429") || message.toLowerCase().includes("rate"))) {
            priceIntervalMs = Math.min(Math.max(priceIntervalMs, 30_000), 120_000);
            write(sseEvent({ event: "rate_limit", data: { message, nextPriceIntervalMs: priceIntervalMs } }));
          }

          write(sseEvent({ event: "error", data: { message } }));
        }
      };

      const loop = async () => {
        if (closed) return;

        // Occasionally refresh metrics (P/E). First attempt immediately.
        const now = Date.now();
        const shouldRefreshPe = lastPeRefreshAt === 0 || now - lastPeRefreshAt >= peIntervalMs;
        await sendQuotes({ includeMetrics: shouldRefreshPe });

        setTimeout(() => void loop(), priceIntervalMs);
      };

      // Start streaming immediately.
      void loop();

      // Heartbeat (some proxies close idle connections).
      const heartbeatId = setInterval(() => {
        write(": ping\n\n");
      }, 25_000);

      // Cleanup when the client disconnects.
      req.signal.addEventListener("abort", () => {
        clearInterval(heartbeatId);
        safeClose();
      });
    },
  });

  return new Response(stream, {
    headers: {
      "Content-Type": "text/event-stream; charset=utf-8",
      "Cache-Control": "no-cache, no-transform",
      Connection: "keep-alive",
      "X-Accel-Buffering": "no",
    },
  });
}
