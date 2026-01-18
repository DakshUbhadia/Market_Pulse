'use server';

import { BSE_STOCKS, US_DEFAULT_STOCKS, type StockListItem } from '@/lib/constants';
import yahooFinance from 'yahoo-finance2';

// Initialize yahoo-finance2 instance
const yf = new yahooFinance({ suppressNotices: ['yahooSurvey'] });

// Helper to safely extract numeric values from yahoo-finance responses
const toNumber = (value: unknown): number | undefined => {
  if (typeof value === 'number' && Number.isFinite(value)) return value;
  if (value && typeof value === 'object' && 'raw' in value) {
    const raw = (value as { raw?: unknown }).raw;
    if (typeof raw === 'number' && Number.isFinite(raw)) return raw;
  }
  return undefined;
};

export type MarketType = 'US' | 'IN';

export type IntradayTrend = 'Bullish' | 'Bearish';

export type SupportedCurrency = 'USD' | 'INR';

export type StockAnalysis = {
  symbol: string;
  name: string;
  sector: string;
  exchange: string;
  currency: SupportedCurrency;
  price: number;
  openPrice: number;
  changePercent: number;
  rFactor: number; // Relative Strength (0-100)
  intradayTrend: IntradayTrend; // Today's price vs open
  strongMoneySignal: 'Buying' | 'Selling' | 'Neutral';
  strongMoneyScore: number; // Raw score for aggregation
  reasons: string[];
};

export type SectorHeatmapData = {
  sector: string;
  stockCount: number;
  avgRFactor: number;
  strongMoneyIntensity: number; // -100 to +100 (negative=selling, positive=buying)
  buyingStocks: number;
  sellingStocks: number;
  sentiment: 'Bullish' | 'Bearish' | 'Neutral';
};

export type SectorScope = {
  sector: string;
  totalStrongMoneyStocks: number;
  sentiment: 'Bullish' | 'Bearish';
  stocks: StockAnalysis[];
  heatmapData: SectorHeatmapData;
};

export type MarketScopeResult = {
  market: MarketType;
  heatmap: SectorHeatmapData[];
  sectors: SectorScope[];
  totalStocksAnalyzed: number;
  totalStocksWithData: number;
  timestamp: string;
};

// Helper: Calculate R-Factor (Position in 52-week range)
const calculateRFactor = (current: number, low: number, high: number): number => {
  if (high === low) return 50;
  return ((current - low) / (high - low)) * 100;
};

const stripYahooSuffix = (symbol: string): string => {
  const s = String(symbol ?? '').trim();
  return s.replace(/\.(BO|NS)$/i, '');
};

const normalizeSector = (raw: unknown): string => {
  const sector = typeof raw === 'string' ? raw.trim() : '';
  if (!sector) return 'Miscellaneous';

  // Normalize Yahoo sector naming into consistent buckets.
  // (Prevents "Other" and avoids fragmented sector labels.)
  const key = sector.toLowerCase();
  const map: Record<string, string> = {
    other: 'Miscellaneous',
    'financial services': 'Financials',
    'consumer cyclical': 'Consumer Discretionary',
    'consumer defensive': 'Consumer Staples',
    'basic materials': 'Materials',
    technology: 'Information Technology',
  };

  return map[key] ?? sector;
};

const buildUnavailableAnalysis = (args: {
  symbol: string;
  name: string;
  exchange: string;
  currency: SupportedCurrency;
}): StockAnalysis => {
  const { symbol, name, exchange, currency } = args;
  return {
    symbol: stripYahooSuffix(symbol),
    name,
    sector: 'Data Unavailable',
    exchange,
    currency,
    price: 0,
    openPrice: 0,
    changePercent: 0,
    rFactor: 0,
    intradayTrend: 'Bearish',
    strongMoneySignal: 'Neutral',
    strongMoneyScore: 0,
    reasons: ['Data Unavailable'],
  };
};

const analyzeStockSymbol = async (args: {
  symbol: string;
  fallbackName: string;
  fallbackExchange: string;
  currency: SupportedCurrency;
}): Promise<StockAnalysis> => {
  const { symbol, fallbackName, fallbackExchange, currency } = args;

  try {
    const summary = await yf.quoteSummary(symbol, {
      modules: [
        'price',
        'summaryProfile',
        'defaultKeyStatistics',
        'netSharePurchaseActivity',
        'majorHoldersBreakdown',
      ],
    });

    const { price, summaryProfile, defaultKeyStatistics, netSharePurchaseActivity, majorHoldersBreakdown } = summary;

    if (!price?.regularMarketPrice) {
      return buildUnavailableAnalysis({
        symbol,
        name: fallbackName,
        exchange: fallbackExchange,
        currency,
      });
    }

    // Data Extraction
    const currentPrice = price.regularMarketPrice;
    const openPrice = toNumber(price.regularMarketOpen) ?? currentPrice;
    const high52 =
      toNumber((defaultKeyStatistics as unknown as { fiftyTwoWeekHigh?: unknown })?.fiftyTwoWeekHigh) ??
      toNumber(price.regularMarketDayHigh) ??
      currentPrice;
    const low52 =
      toNumber((defaultKeyStatistics as unknown as { fiftyTwoWeekLow?: unknown })?.fiftyTwoWeekLow) ??
      toNumber(price.regularMarketDayLow) ??
      currentPrice;
    const rFactor = calculateRFactor(currentPrice, low52, high52);

    const insiderBuyPercent = toNumber(netSharePurchaseActivity?.netPercentInsiderShares) ?? 0;
    const instHeld =
      toNumber((majorHoldersBreakdown as unknown as { institutionsPercentHeld?: unknown })?.institutionsPercentHeld) ?? 0;
    const changePercent = toNumber(price.regularMarketChangePercent) ?? 0;

    const volume = toNumber(price.regularMarketVolume) ?? 0;
    const avgVolume = toNumber(price.averageDailyVolume10Day) ?? toNumber(price.averageDailyVolume3Month) ?? volume;
    const volSpike = avgVolume > 0 ? volume / avgVolume : 1;

    // Calculate Intraday Trend (with 0.1% buffer to avoid noise)
    const intradayBuffer = openPrice * 0.001;
    const intradayTrend: IntradayTrend = currentPrice > openPrice + intradayBuffer ? 'Bullish' : 'Bearish';

    // "Strong Money" Logic
    const reasons: string[] = [];
    let score = 0;

    // Rule A: Insiders are buying
    if (insiderBuyPercent > 0.01) {
      score += 2;
      reasons.push('Insiders Buying');
    } else if (insiderBuyPercent < -0.01) {
      score -= 2;
      reasons.push('Insiders Selling');
    }

    // Rule B: Institutional ownership
    if (instHeld > 0.3) {
      score += 1;
      reasons.push(`Inst. ${(instHeld * 100).toFixed(0)}%`);
    }

    // Rule C: Price momentum
    if (rFactor > 80) {
      score += 1;
      reasons.push(`R:${rFactor.toFixed(0)}`);
    } else if (rFactor < 20) {
      score -= 1;
      reasons.push('Weak Momentum');
    }

    // Bonus for very high momentum
    if (rFactor > 90) {
      score += 1;
    }

    // Bonus for volume spike
    if (volSpike > 1.5) {
      score += 1;
      reasons.push(`Vol ${volSpike.toFixed(1)}x`);
    }

    // Rule D: Intraday Trend Filter (THE TRAP FILTER)
    // Bonus for stocks rising today (safe entry), penalty for falling (profit booking)
    if (intradayTrend === 'Bullish') {
      score += 2;
      reasons.push('Rising Today');
    } else {
      score -= 1;
      reasons.push('Profit Booking');
    }

    // Determine Signal
    let signal: 'Buying' | 'Selling' | 'Neutral' = 'Neutral';
    if (score >= 2) signal = 'Buying';
    if (score <= -2) signal = 'Selling';

    return {
      symbol: stripYahooSuffix(symbol),
      name: price.shortName ?? fallbackName,
      sector: normalizeSector(summaryProfile?.sector),
      exchange: fallbackExchange,
      currency,
      price: currentPrice,
      openPrice,
      changePercent,
      rFactor: Number.parseFloat(rFactor.toFixed(1)),
      intradayTrend,
      strongMoneySignal: signal,
      strongMoneyScore: score,
      reasons,
    };
  } catch {
    return buildUnavailableAnalysis({
      symbol,
      name: fallbackName,
      exchange: fallbackExchange,
      currency,
    });
  }
};

// Get stocks based on market selection
const getStocksForMarket = (market: MarketType): StockListItem[] => {
  if (market === 'US') {
    return US_DEFAULT_STOCKS ?? [];
  }
  // For Indian market, use BSE stocks (with .BO suffix for Yahoo Finance)
  return (BSE_STOCKS ?? []).map((s) => ({
    ...s,
    symbol: s.symbol.endsWith('.BO') ? s.symbol : `${s.symbol}.BO`,
  }));
};

export const getStrongMoneyScope = async (
  market: MarketType = 'US',
  topPerSector: number = 15
): Promise<MarketScopeResult> => {
  const stocks = getStocksForMarket(market);
  const currency: SupportedCurrency = market === 'IN' ? 'INR' : 'USD';

  const stockBySymbol = new Map<string, StockListItem>();
  for (const stock of stocks) {
    const symbol = String(stock?.symbol ?? '').trim();
    if (!symbol) continue;
    if (!stockBySymbol.has(symbol)) stockBySymbol.set(symbol, stock);
  }

  const uniqueSymbols = Array.from(stockBySymbol.keys());

  // Fetch & Analyze Each Stock
  const promises = uniqueSymbols.map((symbol) => {
    const curated = stockBySymbol.get(symbol);
    const fallbackName = curated?.name ?? symbol;
    const fallbackExchange = curated?.exchange ?? (market === 'IN' ? 'BSE' : 'NASDAQ');
    return analyzeStockSymbol({ symbol, fallbackName, fallbackExchange, currency });
  });

  const analyzedStocks = await Promise.all(promises);

  // Group by Sector
  const sectorMap = new Map<string, StockAnalysis[]>();
  analyzedStocks.forEach((stock) => {
    const existing = sectorMap.get(stock.sector) ?? [];
    existing.push(stock);
    sectorMap.set(stock.sector, existing);
  });

  // Build Heatmap Data and Sector Scopes
  const heatmap: SectorHeatmapData[] = [];
  const sectors: SectorScope[] = [];

  sectorMap.forEach((sectorStocks, sector) => {
    // Sort stocks by: 1) Bullish intraday first, 2) then R-Factor descending
    sectorStocks.sort((a, b) => {
      // Prioritize Bullish intraday trend
      if (a.intradayTrend === 'Bullish' && b.intradayTrend !== 'Bullish') return -1;
      if (b.intradayTrend === 'Bullish' && a.intradayTrend !== 'Bullish') return 1;
      // Then by R-Factor descending
      return b.rFactor - a.rFactor;
    });

    const buyingStocks = sectorStocks.filter((s) => s.strongMoneySignal === 'Buying').length;
    const sellingStocks = sectorStocks.filter((s) => s.strongMoneySignal === 'Selling').length;

    // Calculate average R-Factor
    const avgRFactor = sectorStocks.reduce((sum, s) => sum + s.rFactor, 0) / sectorStocks.length;

    // Calculate Strong Money Intensity (-100 to +100)
    // Positive = more buying, Negative = more selling
    const totalScores = sectorStocks.reduce((sum, s) => sum + s.strongMoneyScore, 0);
    const maxPossibleScore = sectorStocks.length * 5; // Max score per stock is ~5
    const strongMoneyIntensity = maxPossibleScore > 0 ? (totalScores / maxPossibleScore) * 100 : 0;

    // Determine sector sentiment
    let sentiment: 'Bullish' | 'Bearish' | 'Neutral' = 'Neutral';
    if (buyingStocks > sellingStocks && strongMoneyIntensity > 10) sentiment = 'Bullish';
    else if (sellingStocks > buyingStocks && strongMoneyIntensity < -10) sentiment = 'Bearish';

    const heatmapData: SectorHeatmapData = {
      sector,
      stockCount: sectorStocks.length,
      avgRFactor: Number.parseFloat(avgRFactor.toFixed(1)),
      strongMoneyIntensity: Number.parseFloat(strongMoneyIntensity.toFixed(1)),
      buyingStocks,
      sellingStocks,
      sentiment,
    };

    heatmap.push(heatmapData);

    // Detailed view: show best N stocks by R-Factor (descending)
    const topStocks = sectorStocks.slice(0, Math.max(1, topPerSector));
    sectors.push({
      sector,
      totalStrongMoneyStocks: topStocks.length,
      sentiment: buyingStocks >= sellingStocks ? 'Bullish' : 'Bearish',
      stocks: topStocks,
      heatmapData,
    });
  });

  // Avoid the heatmap being dominated by missing-data placeholders.
  // Still keep the sector breakdown so users can see which symbols failed.
  const dataUnavailableSectorIndex = heatmap.findIndex((x) => x.sector === 'Data Unavailable');
  if (dataUnavailableSectorIndex >= 0) {
    heatmap.splice(dataUnavailableSectorIndex, 1);
  }

  // Sort heatmap by intensity (highest buying first)
  heatmap.sort((a, b) => b.strongMoneyIntensity - a.strongMoneyIntensity);

  // Sort sectors by strongest inflow first
  sectors.sort((a, b) => b.heatmapData.strongMoneyIntensity - a.heatmapData.strongMoneyIntensity);

  return {
    market,
    heatmap,
    sectors,
    totalStocksAnalyzed: analyzedStocks.length,
    totalStocksWithData: analyzedStocks.filter((s) => s.sector !== 'Data Unavailable').length,
    timestamp: new Date().toISOString(),
  };
};
