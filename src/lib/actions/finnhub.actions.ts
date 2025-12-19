'use server';

import { cache } from 'react';
import { BSE_STOCKS, DEFAULT_SEARCH_STOCKS, US_DEFAULT_STOCKS } from '@/lib/constants';

const FINNHUB_BASE_URL = "https://finnhub.io/api/v1";
const NEXT_PUBLIC_FINNHUB_API_KEY = process.env.NEXT_PUBLIC_FINNHUB_API_KEY;

const FINNHUB_TOKEN = NEXT_PUBLIC_FINNHUB_API_KEY;

type FinnhubSearchResult = {
  description: string;
  displaySymbol: string;
  symbol: string;
  type?: string;
  exchange?: string;
};

type FinnhubSearchResponse = {
  count: number;
  result: FinnhubSearchResult[];
};

type StockWithWatchlistStatus = {
  symbol: string;
  name: string;
  exchange: string;
  type: string;
  isInWatchlist: boolean;
};

type FetchJSONOptions = {
  revalidateSeconds?: number;
};

type FinnhubNewsArticle = {
  id?: number;
  category?: string;
  datetime?: number;
  headline?: string;
  image?: string;
  related?: string;
  source?: string;
  summary?: string;
  url?: string;
};

export type MarketNewsArticle = {
  id: string;
  headline: string;
  datetime: number;
  url: string;
  source: string;
  summary: string;
  image?: string;
  relatedSymbol?: string;
};

const isNonEmptyString = (value: unknown): value is string =>
  typeof value === "string" && value.trim().length > 0;

const isValidNewsArticle = (a: FinnhubNewsArticle): a is Required<
  Pick<FinnhubNewsArticle, "headline" | "datetime" | "url" | "summary" | "source">
> &
  FinnhubNewsArticle => {
  return (
    isNonEmptyString(a.headline) &&
    typeof a.datetime === "number" &&
    a.datetime > 0 &&
    isNonEmptyString(a.url) &&
    (a.url.startsWith("http://") || a.url.startsWith("https://")) &&
    isNonEmptyString(a.summary) &&
    isNonEmptyString(a.source)
  );
};

const formatDateYYYYMMDD = (d: Date): string => {
  const yyyy = d.getUTCFullYear();
  const mm = String(d.getUTCMonth() + 1).padStart(2, "0");
  const dd = String(d.getUTCDate()).padStart(2, "0");
  return `${yyyy}-${mm}-${dd}`;
};

const getArticleKey = (a: MarketNewsArticle): string => {
  const idPart = a.id ? `id:${a.id}` : "";
  const urlPart = a.url ? `url:${a.url}` : "";
  const headlinePart = a.headline ? `h:${a.headline}` : "";
  return [idPart, urlPart, headlinePart].filter(Boolean).join("|");
};

export const fetchJSON = async <T>(
  url: string,
  options: FetchJSONOptions = {}
): Promise<T> => {
  const { revalidateSeconds } = options;

  const requestInit: RequestInit & { next?: { revalidate: number } } =
    typeof revalidateSeconds === "number"
      ? { cache: "force-cache", next: { revalidate: revalidateSeconds } }
      : { cache: "no-store" };

  const res = await fetch(url, requestInit);
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`Finnhub request failed (${res.status}): ${text}`);
  }

  return (await res.json()) as T;
};

// Types for stock quote data
type FinnhubQuote = {
  c: number; // Current price
  d: number; // Change
  dp: number; // Percent change
  h: number; // High price of the day
  l: number; // Low price of the day
  o: number; // Open price of the day
  pc: number; // Previous close price
  t: number; // Timestamp
};

type FinnhubProfile = {
  country?: string;
  currency?: string;
  exchange?: string;
  ipo?: string;
  marketCapitalization?: number;
  name?: string;
  phone?: string;
  shareOutstanding?: number;
  ticker?: string;
  weburl?: string;
  logo?: string;
  finnhubIndustry?: string;
};

type FinnhubMetricResponse = {
  metric?: Record<string, unknown>;
};

export type StockQuoteData = {
  symbol: string;
  name: string;
  exchange: string;
  currency: string;
  currentPrice: number;
  openPrice: number;
  highPrice: number;
  lowPrice: number;
  previousClose: number;
  change: number;
  percentChange: number;
  logoUrl?: string;
  peRatio: number;
  timestamp: number;
};

type QuoteRequest = {
  symbol: string;
  exchange?: string;
};

const getFirstPositiveNumber = (values: unknown[]): number | undefined => {
  for (const v of values) {
    if (typeof v !== "number") continue;
    if (!Number.isFinite(v)) continue;
    if (v <= 0) continue;
    return v;
  }
  return undefined;
};

const extractPeRatio = (metrics: FinnhubMetricResponse | null): number | undefined => {
  const m = metrics?.metric;
  if (!m) return undefined;

  // Finnhub commonly exposes P/E as one of these fields (varies by plan/exchange).
  // Prefer TTM values when present.
  return getFirstPositiveNumber([
    m.peTTM,
    m.peBasicExclExtraTTM,
    m.peInclExtraTTM,
    m.peNormalizedAnnual,
    m.peAnnual,
  ]);
};

const extractEpsTtm = (metrics: FinnhubMetricResponse | null): number | undefined => {
  const m = metrics?.metric;
  if (!m) return undefined;

  return getFirstPositiveNumber([
    // Common Finnhub metric keys (vary by plan/exchange)
    m.epsTTM,
    m.epsBasicExclExtraItemsTTM,
    m.epsInclExtraItemsTTM,
    m.epsNormalizedAnnual,
    m.epsAnnual,
  ]);
};

const resolvePeRatio = (args: {
  currentPrice: number;
  metricResponse: FinnhubMetricResponse | null;
}): number | undefined => {
  const { currentPrice, metricResponse } = args;

  const epsTtm = extractEpsTtm(metricResponse);
  if (Number.isFinite(currentPrice) && currentPrice > 0 && typeof epsTtm === "number" && epsTtm > 0) {
    const computed = currentPrice / epsTtm;
    if (Number.isFinite(computed) && computed > 0) return computed;
  }

  return extractPeRatio(metricResponse);
};

const getFinnhubSymbolCandidates = (symbol: string, exchange?: string): string[] => {
  const normalized = symbol.toUpperCase().trim();
  const ex = String(exchange ?? "").toUpperCase().trim();
  if (!normalized) return [];

  const candidates: string[] = [normalized];

  // Finnhub symbol formats vary across exchanges. For Indian equities, different
  // deployments commonly accept one of: RELIANCE.NS, RELIANCE.BO, NSE:RELIANCE, BSE:RELIANCE.
  if (ex === "BSE") {
    candidates.unshift(`${normalized}.BO`, `BSE:${normalized}`, `${normalized}.NS`, `NSE:${normalized}`);
  } else if (ex === "NSE") {
    candidates.unshift(`${normalized}.NS`, `NSE:${normalized}`, `${normalized}.BO`, `BSE:${normalized}`);
  }

  // De-dupe while preserving order.
  const seen = new Set<string>();
  return candidates.filter((c) => {
    const key = c.toUpperCase();
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });
};

/**
 * Fetch real-time quote data for a stock symbol
 */
type StockQuoteFetchPolicy = {
  quoteRevalidateSeconds?: number;
  profileRevalidateSeconds?: number;
  metricRevalidateSeconds?: number;
  includeMetrics: boolean;
  /**
   * When Finnhub is configured but a request fails (network/429/etc), returning mock
   * data can be misleading. For realtime streaming we prefer returning null.
   */
  fallbackToMockOnError: boolean;
  /**
   * When no symbol candidate works, return mock for US equities only.
   */
  fallbackToMockOnNotFound: boolean;
};

const getStockQuoteImpl = async (
  symbol: string,
  exchange?: string,
  policy?: Partial<StockQuoteFetchPolicy>
): Promise<StockQuoteData | null> => {
  const resolvedPolicy = {
    quoteRevalidateSeconds: policy?.quoteRevalidateSeconds,
    profileRevalidateSeconds: policy?.profileRevalidateSeconds,
    metricRevalidateSeconds: policy?.metricRevalidateSeconds,
    includeMetrics: policy?.includeMetrics ?? true,
    fallbackToMockOnError: policy?.fallbackToMockOnError ?? true,
    fallbackToMockOnNotFound: policy?.fallbackToMockOnNotFound ?? true,
  } satisfies StockQuoteFetchPolicy;

  const {
    quoteRevalidateSeconds,
    profileRevalidateSeconds,
    metricRevalidateSeconds,
    includeMetrics,
    fallbackToMockOnError,
    fallbackToMockOnNotFound,
  } = resolvedPolicy;

  try {
    const normalizedSymbol = symbol.toUpperCase().trim();
    const ex = String(exchange ?? "").toUpperCase().trim();

    if (!FINNHUB_TOKEN) {
      // Don't show misleading mock prices for Indian equities.
      if (ex === "BSE" || ex === "NSE") return null;

      console.warn("FINNHUB_TOKEN not set, returning mock data");
      return createMockQuote(symbol, undefined, undefined, exchange);
    }

    const candidates = getFinnhubSymbolCandidates(normalizedSymbol, exchange);

    for (const candidate of candidates) {
      const quoteUrl = `${FINNHUB_BASE_URL}/quote?symbol=${encodeURIComponent(candidate)}&token=${encodeURIComponent(FINNHUB_TOKEN)}`;
      const profileUrl = `${FINNHUB_BASE_URL}/stock/profile2?symbol=${encodeURIComponent(candidate)}&token=${encodeURIComponent(FINNHUB_TOKEN)}`;
      const metricUrl = `${FINNHUB_BASE_URL}/stock/metric?symbol=${encodeURIComponent(candidate)}&metric=all&token=${encodeURIComponent(FINNHUB_TOKEN)}`;

      const [quoteResponse, profileResponse, metricResponse] = await Promise.all([
        fetchJSON<FinnhubQuote>(quoteUrl, typeof quoteRevalidateSeconds === "number" ? { revalidateSeconds: quoteRevalidateSeconds } : undefined).catch(() => null),
        fetchJSON<FinnhubProfile>(profileUrl, typeof profileRevalidateSeconds === "number" ? { revalidateSeconds: profileRevalidateSeconds } : undefined).catch(() => null),
        includeMetrics
          ? fetchJSON<FinnhubMetricResponse>(
              metricUrl,
              typeof metricRevalidateSeconds === "number" ? { revalidateSeconds: metricRevalidateSeconds } : undefined
            ).catch(() => null)
          : Promise.resolve(null),
      ]);

      if (!quoteResponse) continue;

      // If quote returns all zeros, the symbol might not be supported.
      if (quoteResponse.c === 0 && quoteResponse.o === 0 && quoteResponse.h === 0 && quoteResponse.l === 0) {
        continue;
      }

      const resolvedCurrency =
        ex === "BSE" || ex === "NSE" ? "INR" : (profileResponse?.currency || "USD");

      const resolvedPe = includeMetrics ? resolvePeRatio({ currentPrice: quoteResponse.c, metricResponse }) : undefined;

      return {
        symbol: normalizedSymbol,
        name: profileResponse?.name || normalizedSymbol,
        exchange: exchange || profileResponse?.exchange || "US",
        currency: resolvedCurrency,
        currentPrice: quoteResponse.c,
        openPrice: quoteResponse.o,
        highPrice: quoteResponse.h,
        lowPrice: quoteResponse.l,
        previousClose: quoteResponse.pc,
        change: quoteResponse.d,
        percentChange: quoteResponse.dp,
        logoUrl: profileResponse?.logo,
        peRatio: typeof resolvedPe === "number" ? resolvedPe : Number.NaN,
        timestamp: quoteResponse.t ? quoteResponse.t * 1000 : Date.now(),
      };
    }

    // If none of the candidates worked:
    // - For Indian equities, return null (avoid wrong random prices).
    // - For US, optionally fall back to mock.
    if (ex === "BSE" || ex === "NSE") return null;

    return fallbackToMockOnNotFound ? createMockQuote(symbol, undefined, undefined, exchange) : null;
  } catch (error) {
    console.error("Error fetching stock quote:", error);
    const ex = String(exchange ?? "").toUpperCase().trim();
    if (ex === "BSE" || ex === "NSE") return null;
    return fallbackToMockOnError ? createMockQuote(symbol, undefined, undefined, exchange) : null;
  }
};

export const getStockQuote = cache(async (symbol: string, exchange?: string): Promise<StockQuoteData | null> => {
  return getStockQuoteImpl(symbol, exchange, {
    quoteRevalidateSeconds: 30,
    profileRevalidateSeconds: 3600,
    metricRevalidateSeconds: 6 * 60 * 60,
    includeMetrics: true,
    fallbackToMockOnError: true,
    fallbackToMockOnNotFound: true,
  });
});

/**
 * Realtime quote variant for live streaming.
 * - Uses `cache: "no-store"` (no revalidate)
 * - Avoids returning mock data on transient failures
 */
export const getStockQuoteRealtime = async (args: {
  symbol: string;
  exchange?: string;
  includeMetrics?: boolean;
}): Promise<StockQuoteData | null> => {
  return getStockQuoteImpl(args.symbol, args.exchange, {
    quoteRevalidateSeconds: undefined,
    profileRevalidateSeconds: 3600,
    metricRevalidateSeconds: 6 * 60 * 60,
    includeMetrics: args.includeMetrics ?? false,
    fallbackToMockOnError: false,
    fallbackToMockOnNotFound: false,
  });
};

function createMockQuote(symbol: string, name?: string, logo?: string, exchange?: string): StockQuoteData {
  // Generate consistent mock data based on symbol
  const hash = symbol.split("").reduce((acc, char) => acc + char.charCodeAt(0), 0);
  const basePrice = 50 + (hash % 250);
  const change = ((hash % 20) - 10) * 0.5;

  const ex = String(exchange ?? "US").toUpperCase();
  const currency = ex === "BSE" || ex === "NSE" ? "INR" : "USD";
  
  return {
    symbol: symbol.toUpperCase(),
    name: name || symbol,
    exchange: exchange || "US",
    currency,
    currentPrice: basePrice,
    openPrice: basePrice - change,
    highPrice: basePrice + Math.abs(change) + 2,
    lowPrice: basePrice - Math.abs(change) - 2,
    previousClose: basePrice - change,
    change: change,
    percentChange: (change / basePrice) * 100,
    logoUrl: logo,
    peRatio: 15 + (hash % 30),
    timestamp: Date.now(),
  };
}

/**
 * Fetch quotes for multiple symbols
 */
export const getMultipleStockQuotes = async (requests: QuoteRequest[]): Promise<StockQuoteData[]> => {
  if (requests.length === 0) return [];

  const results = await Promise.all(
    requests.map((r) => getStockQuote(r.symbol, r.exchange))
  );
  
  return results.filter((quote): quote is StockQuoteData => quote !== null);
};

export const getMultipleStockQuotesRealtime = async (args: {
  requests: QuoteRequest[];
  includeMetrics?: boolean;
}): Promise<StockQuoteData[]> => {
  const { requests, includeMetrics } = args;
  if (requests.length === 0) return [];

  const results = await Promise.all(
    requests.map((r) => getStockQuoteRealtime({ symbol: r.symbol, exchange: r.exchange, includeMetrics }))
  );

  return results.filter((quote): quote is StockQuoteData => quote !== null);
};

export const searchStocks = cache(async (query?: string): Promise<StockWithWatchlistStatus[]> => {
  try {
    const trimmedQuery = typeof query === 'string' ? query.trim() : '';

    const normalizedQuery = trimmedQuery.toUpperCase();

    const curatedUniverse = [...BSE_STOCKS, ...US_DEFAULT_STOCKS];

    // Always support searching within the curated BSE list.
    const curatedMatches = curatedUniverse.filter((s) => {
      if (!normalizedQuery) return true;
      return (
        s.symbol.toUpperCase().includes(normalizedQuery) ||
        s.name.toUpperCase().includes(normalizedQuery)
      );
    }).map(
      (s): StockWithWatchlistStatus => ({
        symbol: s.symbol,
        name: s.name,
        exchange: s.exchange,
        type: 'Stock',
        isInWatchlist: false,
      })
    );

    // For empty query, show the requested default list.
    if (!normalizedQuery) {
      return DEFAULT_SEARCH_STOCKS.map(
        (s): StockWithWatchlistStatus => ({
          symbol: s.symbol,
          name: s.name,
          exchange: s.exchange,
          type: 'Stock',
          isInWatchlist: false,
        })
      );
    }

    // If Finnhub isn't configured, fall back to curated matches only.
    if (!FINNHUB_TOKEN) {
      return curatedMatches.slice(0, 15);
    }

    const url = `${FINNHUB_BASE_URL}/search?q=${encodeURIComponent(
      trimmedQuery
    )}&token=${encodeURIComponent(FINNHUB_TOKEN)}`;

    const response = await fetchJSON<FinnhubSearchResponse>(url, {
      revalidateSeconds: 1800,
    });

    const results = Array.isArray(response.result) ? response.result : [];

    const finnhubMatches = results
      .map((result): StockWithWatchlistStatus => {
        const symbol = String(result.symbol ?? '').trim().toUpperCase();
        return {
          symbol,
          name: String(result.description ?? ''),
          exchange: isNonEmptyString(result.exchange) ? result.exchange : 'US',
          type: isNonEmptyString(result.type) ? result.type : 'Stock',
          isInWatchlist: false,
        };
      })
      .filter((item) => item.symbol.length > 0);

    const seen = new Set<string>();
    const merged = [...curatedMatches, ...finnhubMatches].filter((item) => {
      if (seen.has(item.symbol)) return false;
      seen.add(item.symbol);
      return true;
    });

    return merged.slice(0, 15);
  } catch (error) {
    console.error('Error in stock search:', error);
    return [];
  }
});

const toMarketNewsArticle = (a: FinnhubNewsArticle, relatedSymbol?: string): MarketNewsArticle => {
  // validate before calling this
  const id = typeof a.id === "number" ? String(a.id) : `${a.url}`;
  return {
    id,
    headline: a.headline!.trim(),
    datetime: a.datetime!,
    url: a.url!,
    source: a.source!,
    summary: a.summary!,
    image: isNonEmptyString(a.image) ? a.image : undefined,
    relatedSymbol,
  };
};

const cleanSymbols = (symbols: string[]): string[] => {
  const cleaned = symbols
    .map((s) => s.trim().toUpperCase())
    .filter((s) => s.length > 0);

  return Array.from(new Set(cleaned));
};

export type GetNewsOptions = {
  /** How many days back to look when fetching company news. Default: 5 */
  daysBack?: number;
  /** Max items to return. Default: 6 */
  maxItems?: number;
  /** Max round-robin fetches for watchlist/company news. Default: 6 */
  maxRounds?: number;
};

export const getNews = async (symbols?: string[], options?: GetNewsOptions): Promise<MarketNewsArticle[]> => {
  try {
    if (!NEXT_PUBLIC_FINNHUB_API_KEY) {
      throw new Error("NEXT_PUBLIC_FINNHUB_API_KEY is not set");
    }

    const daysBack = typeof options?.daysBack === "number" && options.daysBack > 0 ? options.daysBack : 5;
    const maxItems = typeof options?.maxItems === "number" && options.maxItems > 0 ? options.maxItems : 6;
    const maxRounds = typeof options?.maxRounds === "number" && options.maxRounds > 0 ? options.maxRounds : 6;

    const now = new Date();
    const from = new Date(now);
    from.setUTCDate(from.getUTCDate() - daysBack);

    const fromStr = formatDateYYYYMMDD(from);
    const toStr = formatDateYYYYMMDD(now);

    const hasSymbols = Array.isArray(symbols) && symbols.length > 0;

    if (hasSymbols) {
      const tickers = cleanSymbols(symbols!);
      if (tickers.length === 0) return [];

      const picked: MarketNewsArticle[] = [];
      const seen = new Set<string>();

      // Round-robin, limited fetches/rounds (keeps rate usage predictable)
      for (let i = 0; i < maxRounds; i++) {
        const symbol = tickers[i % tickers.length];
        const url = `${FINNHUB_BASE_URL}/company-news?symbol=${encodeURIComponent(
          symbol
        )}&from=${encodeURIComponent(fromStr)}&to=${encodeURIComponent(
          toStr
        )}&token=${encodeURIComponent(NEXT_PUBLIC_FINNHUB_API_KEY)}`;

        const news = await fetchJSON<FinnhubNewsArticle[]>(url);
        const firstValid = (news || []).find(isValidNewsArticle);
        if (!firstValid) continue;

        const formatted = toMarketNewsArticle(firstValid, symbol);
        const key = getArticleKey(formatted);
        if (seen.has(key)) continue;

        seen.add(key);
        picked.push(formatted);
      }

      return picked.sort((a, b) => b.datetime - a.datetime);
    }

    // General market news
    const url = `${FINNHUB_BASE_URL}/news?category=general&token=${encodeURIComponent(
      NEXT_PUBLIC_FINNHUB_API_KEY
    )}`;

    const news = await fetchJSON<FinnhubNewsArticle[]>(url);

    const seen = new Set<string>();
    const deduped: MarketNewsArticle[] = [];

    for (const item of news || []) {
      if (!isValidNewsArticle(item)) continue;
      const formatted = toMarketNewsArticle(item);
      const key = getArticleKey(formatted);
      if (seen.has(key)) continue;
      seen.add(key);
      deduped.push(formatted);
      if (deduped.length >= maxItems) break;
    }

    return deduped.sort((a, b) => b.datetime - a.datetime);
  } catch (err) {
    console.error("getNews error:", err);
    throw new Error("Failed to fetch news");
  }
};