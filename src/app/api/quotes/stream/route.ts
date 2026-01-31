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

const sseEvent = (args: { event?: string; data: unknown; retry?: number }) => {
  const payload = JSON.stringify(args.data);
  const ev = args.event ? `event: ${args.event}\n` : "";
  const retryLine = args.retry ? `retry: ${args.retry}\n` : "";
  return `${retryLine}${ev}data: ${payload}\n\n`;
};

// Track last known good prices per symbol for fallback
const lastKnownPrices = new Map<string, { price: number; timestamp: number; openPrice?: number; percentChange?: number }>();
const STALE_PRICE_THRESHOLD_MS = 120_000; // 2 minutes (was 1 minute) - keep stale prices longer

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
      let consecutiveErrors = 0;
      const MAX_CONSECUTIVE_ERRORS = 3;

      // Faster interval for simulator real-time experience (6 seconds, was 8)
      // This is exclusive-page aware, so watchlist won't compete
      const priceIntervalMs = 6_000;

      const write = (chunk: string) => {
        if (closed) return;
        try {
          controller.enqueue(encoder.encode(chunk));
        } catch {
          // Controller may be closed
        }
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

      const sendQuotes = async () => {
        try {
          const quotes = await getMultipleStockQuotesRealtime({
            requests: items,
            includeMetrics: false,
          });
          
          // Reset error counter on success
          consecutiveErrors = 0;
          
          // Process quotes and update last known prices
          const now = Date.now();
          const processedQuotes = quotes.map(q => {
            const key = `${q.symbol}::${q.exchange || ''}`;
            
            // Update cache with valid prices
            if (typeof q.currentPrice === 'number' && q.currentPrice > 0) {
              lastKnownPrices.set(key, { 
                price: q.currentPrice, 
                timestamp: now,
                openPrice: q.openPrice,
                percentChange: q.percentChange,
              });
            } else {
              // Try to use cached price if current is invalid
              const cached = lastKnownPrices.get(key);
              if (cached && (now - cached.timestamp) < STALE_PRICE_THRESHOLD_MS) {
                return { 
                  ...q, 
                  currentPrice: cached.price,
                  openPrice: cached.openPrice ?? q.openPrice,
                  percentChange: cached.percentChange ?? q.percentChange, 
                  _cached: true 
                };
              }
            }
            
            return q;
          });

          write(
            sseEvent({
              event: "quotes",
              data: {
                quotes: processedQuotes,
                at: now,
                meta: {
                  priceIntervalMs,
                },
              },
              retry: 5000, // Client should retry in 5 seconds if connection drops
            })
          );
        } catch (error) {
          consecutiveErrors++;
          const message = error instanceof Error ? error.message : "Unknown error";
          
          // If we have cached prices, send them instead of error
          if (consecutiveErrors <= MAX_CONSECUTIVE_ERRORS) {
            const now = Date.now();
            const fallbackQuotes = items.map(item => {
              const key = `${item.symbol}::${item.exchange || ''}`;
              const cached = lastKnownPrices.get(key);
              if (cached && (now - cached.timestamp) < STALE_PRICE_THRESHOLD_MS) {
                return {
                  symbol: item.symbol,
                  exchange: item.exchange,
                  currentPrice: cached.price,
                  openPrice: cached.openPrice,
                  percentChange: cached.percentChange,
                  _cached: true,
                  _stale: true,
                };
              }
              return { symbol: item.symbol, exchange: item.exchange };
            }).filter(q => typeof q.currentPrice === 'number');
            
            if (fallbackQuotes.length > 0) {
              write(
                sseEvent({
                  event: "quotes",
                  data: {
                    quotes: fallbackQuotes,
                    at: now,
                    meta: { priceIntervalMs, fallback: true },
                  },
                })
              );
              return;
            }
          }

          write(sseEvent({ event: "error", data: { message, consecutiveErrors } }));
        }
      };

      const loop = async () => {
        if (closed) return;

        await sendQuotes();

        // Adaptive interval: slow down if errors persist
        const nextInterval = consecutiveErrors > 0 
          ? Math.min(priceIntervalMs * (1 + consecutiveErrors * 0.5), 30_000)
          : priceIntervalMs;

        setTimeout(() => void loop(), nextInterval);
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
