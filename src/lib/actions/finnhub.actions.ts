'use server';

import { cache } from 'react';
import { BSE_STOCKS, DEFAULT_SEARCH_STOCKS, US_DEFAULT_STOCKS } from '@/lib/constants';
import YahooFinance from "yahoo-finance2";

const yahooFinance = new YahooFinance();

const FINNHUB_BASE_URL = "https://finnhub.io/api/v1";
const NEXT_PUBLIC_FINNHUB_API_KEY = process.env.NEXT_PUBLIC_FINNHUB_API_KEY;
const FINNHUB_API_KEY = process.env.FINNHUB_API_KEY || NEXT_PUBLIC_FINNHUB_API_KEY;

const FINNHUB_TOKEN = FINNHUB_API_KEY;

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

const fetchJSON = async <T>(
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

type YahooQuoteLike = {
  symbol?: string;
  longName?: string;
  shortName?: string;
  currency?: string;
  fullExchangeName?: string;
  exchange?: string;
  regularMarketPrice?: number;
  regularMarketOpen?: number;
  regularMarketDayHigh?: number;
  regularMarketDayLow?: number;
  regularMarketPreviousClose?: number;
  regularMarketChange?: number;
  regularMarketChangePercent?: number;
  regularMarketTime?: number;
  trailingPE?: number;
  forwardPE?: number;
};

const toYahooTicker = (symbol: string, exchange?: string): string => {
  const raw = String(symbol ?? "").trim();
  if (!raw) return "";

  const upper = raw.toUpperCase();
  // If user already provided a suffix (e.g., TCS.NS) keep as-is.
  if (upper.endsWith(".NS") || upper.endsWith(".BO")) return upper;

  const ex = String(exchange ?? "").toUpperCase().trim();
  // India is BSE-only in this app; coerce any NSE inputs to BSE.
  if (isIndianExchange(ex)) return `${upper}.BO`;
  return upper;
};

// Adapter: Yahoo's descriptive fields -> Finnhub-like labels
const translateYahooToFinnhubQuote = (q: YahooQuoteLike | null | undefined) => {
  if (!q) {
    return {
      c: 0,
      d: 0,
      dp: 0,
      h: 0,
      l: 0,
      o: 0,
      pc: 0,
      t: 0,
    } satisfies FinnhubQuote;
  }

  return {
    c: typeof q.regularMarketPrice === "number" ? q.regularMarketPrice : 0,
    d: typeof q.regularMarketChange === "number" ? q.regularMarketChange : 0,
    dp: typeof q.regularMarketChangePercent === "number" ? q.regularMarketChangePercent : 0,
    h: typeof q.regularMarketDayHigh === "number" ? q.regularMarketDayHigh : 0,
    l: typeof q.regularMarketDayLow === "number" ? q.regularMarketDayLow : 0,
    o: typeof q.regularMarketOpen === "number" ? q.regularMarketOpen : 0,
    pc: typeof q.regularMarketPreviousClose === "number" ? q.regularMarketPreviousClose : 0,
    // Yahoo gives seconds in regularMarketTime; keep milliseconds in our StockQuoteData.
    t: typeof q.regularMarketTime === "number" ? q.regularMarketTime : 0,
  } satisfies FinnhubQuote;
};

const getFirstPositiveNumberFromYahoo = (q: YahooQuoteLike): number | undefined => {
  const candidates = [q.trailingPE, q.forwardPE];
  for (const v of candidates) {
    if (typeof v !== "number") continue;
    if (!Number.isFinite(v)) continue;
    if (v <= 0) continue;
    return v;
  }
  return undefined;
};

type CachedRealtimeQuote = {
  quote: StockQuoteData;
  cachedAtMs: number;
};

// Keep quotes warm between SSE ticks and across multiple clients.
// This prevents hammering Yahoo when multiple streams request the same symbols.
const REALTIME_CACHE_TTL_MS = 12_000;
const REALTIME_CACHE_STALE_MAX_MS = 2 * 60_000;
const YAHOO_BATCH_SIZE = 50;

const realtimeQuoteCache = new Map<string, CachedRealtimeQuote>();

let yahooBackoffUntilMs = 0;

const cacheKeyForQuote = (symbol: string, exchange?: string): string => {
  const sym = String(symbol ?? '').toUpperCase().trim();
  const ex = String(exchange ?? '').toUpperCase().trim();
  return `${sym}::${ex}`;
};

const getCachedRealtimeQuote = (args: {
  symbol: string;
  exchange?: string;
  maxAgeMs: number;
}): StockQuoteData | null => {
  const key = cacheKeyForQuote(args.symbol, args.exchange);
  const entry = realtimeQuoteCache.get(key);
  if (!entry) return null;
  if (Date.now() - entry.cachedAtMs > args.maxAgeMs) return null;
  return entry.quote;
};

const setCachedRealtimeQuote = (quote: StockQuoteData) => {
  realtimeQuoteCache.set(cacheKeyForQuote(quote.symbol, quote.exchange), {
    quote,
    cachedAtMs: Date.now(),
  });
};

const isTooManyRequestsError = (error: unknown): boolean => {
  if (!error || typeof error !== 'object') return false;
  const e = error as { code?: unknown; message?: unknown };
  if (e.code === 429) return true;
  if (typeof e.message === 'string' && /too many requests|\b429\b/i.test(e.message)) return true;
  return false;
};

const buildQuoteFromYahooRaw = (args: {
  raw: YahooQuoteLike;
  requestedSymbol: string;
  requestedExchange?: string;
}): StockQuoteData | null => {
  const normalizedSymbol = String(args.requestedSymbol ?? '').trim().toUpperCase();
  if (!normalizedSymbol) return null;

  const ex = normalizeExchange(args.requestedExchange);
  const finnhubLike = translateYahooToFinnhubQuote(args.raw);

  // If Yahoo couldn't resolve a real quote, treat as missing.
  if (finnhubLike.c === 0 && finnhubLike.o === 0 && finnhubLike.h === 0 && finnhubLike.l === 0) {
    return null;
  }

  let currency = 'USD';
  if (typeof args.raw.currency === 'string' && args.raw.currency.trim()) {
    currency = args.raw.currency;
  } else if (isIndianExchange(ex)) {
    currency = 'INR';
  }

  let name = normalizedSymbol;
  if (typeof args.raw.longName === 'string' && args.raw.longName.trim()) {
    name = args.raw.longName;
  } else if (typeof args.raw.shortName === 'string' && args.raw.shortName.trim()) {
    name = args.raw.shortName;
  }

  const pe = getFirstPositiveNumberFromYahoo(args.raw);
  const timestampMs = finnhubLike.t ? finnhubLike.t * 1000 : Date.now();

  const quote: StockQuoteData = {
    symbol: normalizedSymbol,
    name,
    exchange: args.requestedExchange || args.raw.fullExchangeName || args.raw.exchange || 'US',
    currency,
    currentPrice: finnhubLike.c,
    openPrice: finnhubLike.o,
    highPrice: finnhubLike.h,
    lowPrice: finnhubLike.l,
    previousClose: finnhubLike.pc,
    change: finnhubLike.d,
    percentChange: finnhubLike.dp,
    logoUrl: undefined,
    peRatio: typeof pe === 'number' ? pe : Number.NaN,
    timestamp: timestampMs,
  };

  return quote;
};

const getRealtimeQuotesFromYahooBatch = async (requests: QuoteRequest[]): Promise<StockQuoteData[]> => {
  if (requests.length === 0) return [];

  const now = Date.now();
  const inBackoff = now < yahooBackoffUntilMs;

  // Normalize + de-dupe while preserving order.
  const seen = new Set<string>();
  const normalized: Array<{ symbol: string; exchange?: string }> = [];
  for (const r of requests) {
    const symbol = String(r.symbol ?? '').trim().toUpperCase();
    if (!symbol) continue;
    const exchange = typeof r.exchange === 'string' && r.exchange.trim() ? r.exchange.trim().toUpperCase() : undefined;
    const key = cacheKeyForQuote(symbol, exchange);
    if (seen.has(key)) continue;
    seen.add(key);
    normalized.push({ symbol, exchange });
  }

  // Start with cached results.
  const outputByKey = new Map<string, StockQuoteData>();
  for (const r of normalized) {
    const cached = getCachedRealtimeQuote({
      symbol: r.symbol,
      exchange: r.exchange,
      maxAgeMs: inBackoff ? REALTIME_CACHE_STALE_MAX_MS : REALTIME_CACHE_TTL_MS,
    });
    if (cached) outputByKey.set(cacheKeyForQuote(r.symbol, r.exchange), cached);
  }

  if (inBackoff) {
    // During backoff we do not call Yahoo at all.
    return normalized
      .map((r) => outputByKey.get(cacheKeyForQuote(r.symbol, r.exchange)) ?? null)
      .filter((q): q is StockQuoteData => q !== null);
  }

  const missing = normalized.filter((r) => !outputByKey.has(cacheKeyForQuote(r.symbol, r.exchange)));
  if (missing.length === 0) {
    return normalized
      .map((r) => outputByKey.get(cacheKeyForQuote(r.symbol, r.exchange)) ?? null)
      .filter((q): q is StockQuoteData => q !== null);
  }

  // Fetch missing in batches.
  for (let i = 0; i < missing.length; i += YAHOO_BATCH_SIZE) {
    const batch = missing.slice(i, i + YAHOO_BATCH_SIZE);

    const tickerToRequest = new Map<string, { symbol: string; exchange?: string }>();
    const tickers: string[] = [];
    for (const r of batch) {
      const yahooTicker = toYahooTicker(r.symbol, r.exchange);
      if (!yahooTicker) continue;
      tickers.push(yahooTicker);
      tickerToRequest.set(String(yahooTicker).toUpperCase(), r);
    }

    if (tickers.length === 0) continue;

    try {
      const yahoo = yahooFinance as unknown as { quote: (ticker: string | string[]) => Promise<unknown> };
      const res = await yahoo.quote(tickers.length === 1 ? tickers[0] : tickers);

      const rawArray: YahooQuoteLike[] = Array.isArray(res) ? (res as YahooQuoteLike[]) : [res as YahooQuoteLike];
      const rawBySymbol = new Map<string, YahooQuoteLike>();
      for (const raw of rawArray) {
        if (!raw || typeof raw !== 'object') continue;
        const sym = String((raw as YahooQuoteLike).symbol ?? '').toUpperCase().trim();
        if (!sym) continue;
        rawBySymbol.set(sym, raw);
      }

      for (const [ticker, req] of tickerToRequest.entries()) {
        const raw = rawBySymbol.get(ticker);
        if (!raw) continue;
        const quote = buildQuoteFromYahooRaw({
          raw,
          requestedSymbol: req.symbol,
          requestedExchange: req.exchange,
        });
        if (!quote) continue;
        outputByKey.set(cacheKeyForQuote(req.symbol, req.exchange), quote);
        setCachedRealtimeQuote(quote);
      }
    } catch (error) {
      if (isTooManyRequestsError(error)) {
        // Back off for a minute to avoid a request storm.
        yahooBackoffUntilMs = Date.now() + 60_000;
      } else {
        console.error('Yahoo batch quote failed:', error);
      }
      // On any error: keep serving cached and move on.
      break;
    }
  }

  return normalized
    .map((r) => outputByKey.get(cacheKeyForQuote(r.symbol, r.exchange)) ?? null)
    .filter((q): q is StockQuoteData => q !== null);
};

const getRealtimeQuoteFromYahoo = async (args: {
  symbol: string;
  exchange?: string;
}): Promise<StockQuoteData | null> => {
  const normalizedSymbol = String(args.symbol ?? '').trim().toUpperCase();
  if (!normalizedSymbol) return null;

  // Prefer cached quote to reduce Yahoo traffic.
  const cached = getCachedRealtimeQuote({
    symbol: normalizedSymbol,
    exchange: args.exchange,
    maxAgeMs: REALTIME_CACHE_TTL_MS,
  });
  if (cached) return cached;

  const quotes = await getRealtimeQuotesFromYahooBatch([{ symbol: normalizedSymbol, exchange: args.exchange }]);
  return quotes[0] ?? null;
};

const normalizeExchange = (exchange?: string) => String(exchange ?? "").toUpperCase().trim();
const isIndianExchange = (exchange?: string) => {
  const ex = normalizeExchange(exchange);
  return ex === "BSE" || ex === "NSE";
};

const toRevalidateOptions = (seconds?: number) =>
  typeof seconds === "number" ? { revalidateSeconds: seconds } : undefined;

const isZeroQuote = (q: FinnhubQuote) => q.c === 0 && q.o === 0 && q.h === 0 && q.l === 0;

const fetchCandidateQuoteBundle = async (args: {
  candidate: string;
  token: string;
  includeMetrics: boolean;
  quoteRevalidateSeconds?: number;
  profileRevalidateSeconds?: number;
  metricRevalidateSeconds?: number;
}): Promise<
  | {
      quote: FinnhubQuote;
      profile: FinnhubProfile | null;
      metric: FinnhubMetricResponse | null;
    }
  | null
> => {
  const {
    candidate,
    token,
    includeMetrics,
    quoteRevalidateSeconds,
    profileRevalidateSeconds,
    metricRevalidateSeconds,
  } = args;

  const quoteUrl = `${FINNHUB_BASE_URL}/quote?symbol=${encodeURIComponent(candidate)}&token=${encodeURIComponent(token)}`;
  const profileUrl = `${FINNHUB_BASE_URL}/stock/profile2?symbol=${encodeURIComponent(candidate)}&token=${encodeURIComponent(token)}`;
  const metricUrl = `${FINNHUB_BASE_URL}/stock/metric?symbol=${encodeURIComponent(candidate)}&metric=all&token=${encodeURIComponent(token)}`;

  const quotePromise = fetchJSON<FinnhubQuote>(quoteUrl, toRevalidateOptions(quoteRevalidateSeconds)).catch(() => null);
  const profilePromise = fetchJSON<FinnhubProfile>(profileUrl, toRevalidateOptions(profileRevalidateSeconds)).catch(() => null);
  const metricPromise = includeMetrics
    ? fetchJSON<FinnhubMetricResponse>(metricUrl, toRevalidateOptions(metricRevalidateSeconds)).catch(() => null)
    : Promise.resolve(null);

  const [quote, profile, metric] = await Promise.all([quotePromise, profilePromise, metricPromise]);
  if (!quote) return null;
  if (isZeroQuote(quote)) return null;
  return { quote, profile, metric };
};

const tryFetchFirstQuoteForCandidates = async (args: {
  normalizedSymbol: string;
  exchange?: string;
  ex: string;
  token: string;
  candidates: string[];
  includeMetrics: boolean;
  quoteRevalidateSeconds?: number;
  profileRevalidateSeconds?: number;
  metricRevalidateSeconds?: number;
}): Promise<StockQuoteData | null> => {
  const {
    normalizedSymbol,
    exchange,
    ex,
    token,
    candidates,
    includeMetrics,
    quoteRevalidateSeconds,
    profileRevalidateSeconds,
    metricRevalidateSeconds,
  } = args;

  for (const candidate of candidates) {
    const bundle = await fetchCandidateQuoteBundle({
      candidate,
      token,
      includeMetrics,
      quoteRevalidateSeconds,
      profileRevalidateSeconds,
      metricRevalidateSeconds,
    });
    if (!bundle) continue;

    const resolvedCurrency = ex === "BSE" || ex === "NSE" ? "INR" : (bundle.profile?.currency || "USD");
    const resolvedPe = includeMetrics
      ? resolvePeRatio({ currentPrice: bundle.quote.c, metricResponse: bundle.metric })
      : undefined;

    return {
      symbol: normalizedSymbol,
      name: bundle.profile?.name || normalizedSymbol,
      exchange: exchange || bundle.profile?.exchange || "US",
      currency: resolvedCurrency,
      currentPrice: bundle.quote.c,
      openPrice: bundle.quote.o,
      highPrice: bundle.quote.h,
      lowPrice: bundle.quote.l,
      previousClose: bundle.quote.pc,
      change: bundle.quote.d,
      percentChange: bundle.quote.dp,
      logoUrl: bundle.profile?.logo,
      peRatio: typeof resolvedPe === "number" ? resolvedPe : Number.NaN,
      timestamp: bundle.quote.t ? bundle.quote.t * 1000 : Date.now(),
    };
  }

  return null;
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

  // Finnhub symbol formats vary across deployments. For Indian equities, prefer BSE formats.
  if (isIndianExchange(ex)) {
    candidates.unshift(`${normalized}.BO`, `BSE:${normalized}`);
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
  const quoteRevalidateSeconds = policy?.quoteRevalidateSeconds;
  const profileRevalidateSeconds = policy?.profileRevalidateSeconds;
  const metricRevalidateSeconds = policy?.metricRevalidateSeconds;
  const includeMetrics = policy?.includeMetrics ?? true;
  const fallbackToMockOnError = policy?.fallbackToMockOnError ?? true;
  const fallbackToMockOnNotFound = policy?.fallbackToMockOnNotFound ?? true;

  const normalizedSymbol = symbol.toUpperCase().trim();
  const ex = normalizeExchange(exchange);

  if (!FINNHUB_TOKEN) {
    if (ex === "BSE" || ex === "NSE") return null;
    console.warn("FINNHUB_TOKEN not set, returning mock data");
    return createMockQuote(symbol, undefined, undefined, exchange);
  }

  try {
    const candidates = getFinnhubSymbolCandidates(normalizedSymbol, exchange);
    const quote = await tryFetchFirstQuoteForCandidates({
      normalizedSymbol,
      exchange,
      ex,
      token: FINNHUB_TOKEN,
      candidates,
      includeMetrics,
      quoteRevalidateSeconds,
      profileRevalidateSeconds,
      metricRevalidateSeconds,
    });
    if (quote) return quote;

    if (ex === "BSE" || ex === "NSE") return null;
    return fallbackToMockOnNotFound ? createMockQuote(symbol, undefined, undefined, exchange) : null;
  } catch (error) {
    console.error("Error fetching stock quote:", error);
    if (isIndianExchange(exchange)) return null;
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
  // Realtime watchlist data now comes from Yahoo Finance.
  // Keep the same return shape so the frontend does not change.
  // includeMetrics is ignored (Yahoo doesn't expose Finnhub metrics in the same way).
  return getRealtimeQuoteFromYahoo({ symbol: args.symbol, exchange: args.exchange });
};

function createMockQuote(symbol: string, name?: string, logo?: string, exchange?: string): StockQuoteData {
  // Generate consistent mock data based on symbol
  const hash = symbol.split("").reduce((acc, char) => acc + (char.codePointAt(0) ?? 0), 0);
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
  const { requests } = args;
  if (requests.length === 0) return [];

  // Avoid per-symbol Yahoo requests (which triggers 429). Fetch in batches + use cache.
  try {
    return await getRealtimeQuotesFromYahooBatch(requests);
  } catch (error) {
    if (isTooManyRequestsError(error)) {
      yahooBackoffUntilMs = Date.now() + 60_000;
      // Best-effort: serve cached quotes only.
      const cached = requests
        .map((r) =>
          getCachedRealtimeQuote({
            symbol: String(r.symbol ?? '').toUpperCase().trim(),
            exchange: r.exchange,
            maxAgeMs: REALTIME_CACHE_STALE_MAX_MS,
          })
        )
        .filter((q): q is StockQuoteData => q !== null);
      return cached;
    }

    console.error('Realtime quotes failed:', error);
    return [];
  }
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
    if (!FINNHUB_API_KEY) {
      throw new Error("Finnhub API key is not set (set FINNHUB_API_KEY)");
    }

    const daysBack = typeof options?.daysBack === "number" && options.daysBack > 0 ? options.daysBack : 5;
    const maxItems = typeof options?.maxItems === "number" && options.maxItems > 0 ? options.maxItems : 6;
    const maxRounds = typeof options?.maxRounds === "number" && options.maxRounds > 0 ? options.maxRounds : 6;

    const now = new Date();
    const from = new Date(now);
    from.setUTCDate(from.getUTCDate() - daysBack);

    const fromStr = formatDateYYYYMMDD(from);
    const toStr = formatDateYYYYMMDD(now);

    const tickers = Array.isArray(symbols) ? cleanSymbols(symbols) : [];
    if (tickers.length > 0) {
      return (await getCompanyNews({ tickers, fromStr, toStr, maxRounds, token: FINNHUB_API_KEY }))
        .sort((a, b) => b.datetime - a.datetime);
    }

    return (await getGeneralMarketNews({ maxItems, token: FINNHUB_API_KEY }))
      .sort((a, b) => b.datetime - a.datetime);
  } catch (err) {
    console.error("getNews error:", err);
    throw new Error("Failed to fetch news");
  }
};

const getCompanyNews = async (args: {
  tickers: string[];
  fromStr: string;
  toStr: string;
  maxRounds: number;
  token: string;
}): Promise<MarketNewsArticle[]> => {
  const { tickers, fromStr, toStr, maxRounds, token } = args;
  if (tickers.length === 0) return [];

  // Fetch in parallel to avoid slow per-user sequential loops.
  // Prefer covering distinct symbols rather than cycling the same ones.
  const uniqueTickers = Array.from(
    new Set(tickers.map((t) => t.trim().toUpperCase()).filter(Boolean))
  );
  const symbolsToFetch = uniqueTickers.slice(0, Math.max(1, maxRounds));

  const results = await Promise.all(
    symbolsToFetch.map(async (symbol) => {
      const url = `${FINNHUB_BASE_URL}/company-news?symbol=${encodeURIComponent(symbol)}&from=${encodeURIComponent(fromStr)}&to=${encodeURIComponent(toStr)}&token=${encodeURIComponent(token)}`;
      const news = await fetchJSON<FinnhubNewsArticle[]>(url).catch(() => []);
      const firstValid = (news || []).find(isValidNewsArticle);
      if (!firstValid) return null;
      return toMarketNewsArticle(firstValid, symbol);
    })
  );

  const picked: MarketNewsArticle[] = [];
  const seen = new Set<string>();
  for (const formatted of results) {
    if (!formatted) continue;
    const key = getArticleKey(formatted);
    if (seen.has(key)) continue;
    seen.add(key);
    picked.push(formatted);
  }

  return picked;
};

const getGeneralMarketNews = async (args: { maxItems: number; token: string }): Promise<MarketNewsArticle[]> => {
  const { maxItems, token } = args;
  const url = `${FINNHUB_BASE_URL}/news?category=general&token=${encodeURIComponent(token)}`;
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

  return deduped;
};