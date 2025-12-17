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

export const getNews = async (symbols?: string[]): Promise<MarketNewsArticle[]> => {
  try {
    if (!NEXT_PUBLIC_FINNHUB_API_KEY) {
      throw new Error("NEXT_PUBLIC_FINNHUB_API_KEY is not set");
    }

    const now = new Date();
    const from = new Date(now);
    from.setUTCDate(from.getUTCDate() - 5);

    const fromStr = formatDateYYYYMMDD(from);
    const toStr = formatDateYYYYMMDD(now);

    const hasSymbols = Array.isArray(symbols) && symbols.length > 0;

    if (hasSymbols) {
      const tickers = cleanSymbols(symbols!);
      if (tickers.length === 0) return [];

      const picked: MarketNewsArticle[] = [];
      const seen = new Set<string>();

      // Round-robin, maximum 6 fetches/rounds
      for (let i = 0; i < 6; i++) {
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
      if (deduped.length >= 6) break;
    }

    return deduped.sort((a, b) => b.datetime - a.datetime);
  } catch (err) {
    console.error("getNews error:", err);
    throw new Error("Failed to fetch news");
  }
};