'use server';

import { getStocksForMarket, type MarketType, type StockListItem } from '@/lib/constants';
import yahooFinance from 'yahoo-finance2';

// Initialize yahoo-finance2 instance
const yf = new yahooFinance({
  suppressNotices: ['yahooSurvey'],
  validation: { logErrors: false },
});

// Helper to safely extract numeric values from yahoo-finance responses
const toNumber = (value: unknown): number | undefined => {
  if (typeof value === 'number' && Number.isFinite(value)) return value;
  if (value && typeof value === 'object' && 'raw' in value) {
    const raw = (value as { raw?: unknown }).raw;
    if (typeof raw === 'number' && Number.isFinite(raw)) return raw;
  }
  return undefined;
};

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
  marketCap?: number; // Market cap for weighted calculations
};

export type SectorHeatmapData = {
  sector: string;
  stockCount: number;
  avgRFactor: number;
  strongMoneyIntensity: number; // -100 to +100 (negative=selling, positive=buying)
  buyingStocks: number;
  sellingStocks: number;
  sentiment: 'Bullish' | 'Bearish' | 'Neutral';
  // New: Market Cap weighted % Change
  weightedChangePercent: number;
  // New: A/D Ratio (Advancing/Declining)
  adRatio: number;
  advancingStocks: number;
  decliningStocks: number;
  totalMarketCap: number;
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
  // New: Overall Market A/D Ratio
  marketADRatio: number;
  marketAdvancing: number;
  marketDeclining: number;
  marketSentiment: 'Bullish' | 'Bearish' | 'Neutral';
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
    marketCap: 0,
  };
};

const asRecord = (value: unknown): Record<string, unknown> | undefined => {
  return value && typeof value === 'object' ? (value as Record<string, unknown>) : undefined;
};

const computeStrongMoney = (args: {
  insiderBuyPercent: number;
  instHeld: number;
  rFactor: number;
  volSpike: number;
  intradayTrend: IntradayTrend;
}): { score: number; reasons: string[]; signal: 'Buying' | 'Selling' | 'Neutral' } => {
  const { insiderBuyPercent, instHeld, rFactor, volSpike, intradayTrend } = args;

  const reasons: string[] = [];
  let score = 0;

  if (insiderBuyPercent > 0.01) {
    score += 2;
    reasons.push('Insiders Buying');
  } else if (insiderBuyPercent < -0.01) {
    score -= 2;
    reasons.push('Insiders Selling');
  }

  if (instHeld > 0.3) {
    score += 1;
    reasons.push(`Inst. ${(instHeld * 100).toFixed(0)}%`);
  }

  if (rFactor > 80) {
    score += 1;
    reasons.push(`R:${rFactor.toFixed(0)}`);
  } else if (rFactor < 20) {
    score -= 1;
    reasons.push('Weak Momentum');
  }

  if (rFactor > 90) {
    score += 1;
  }

  if (volSpike > 1.5) {
    score += 1;
    reasons.push(`Vol ${volSpike.toFixed(1)}x`);
  }

  if (intradayTrend === 'Bullish') {
    score += 2;
    reasons.push('Rising Today');
  } else {
    score -= 1;
    reasons.push('Profit Booking');
  }

  let signal: 'Buying' | 'Selling' | 'Neutral' = 'Neutral';
  if (score >= 2) signal = 'Buying';
  if (score <= -2) signal = 'Selling';

  return { score, reasons, signal };
};

const analyzeStockSymbol = async (args: {
  symbol: string;
  fallbackName: string;
  fallbackExchange: string;
  currency: SupportedCurrency;
}): Promise<StockAnalysis> => {
  const { symbol, fallbackName, fallbackExchange, currency } = args;

  try {
    const summaryRaw: unknown = await yf.quoteSummary(
      symbol,
      {
        modules: [
          'price',
          'summaryProfile',
          'defaultKeyStatistics',
          'netSharePurchaseActivity',
          'majorHoldersBreakdown',
        ],
      },
      { validateResult: false }
    );

    const summary = asRecord(summaryRaw) ?? {};
    const price = asRecord(summary['price']);
    const summaryProfile = asRecord(summary['summaryProfile']);
    const defaultKeyStatistics = asRecord(summary['defaultKeyStatistics']);
    const netSharePurchaseActivity = asRecord(summary['netSharePurchaseActivity']);
    const majorHoldersBreakdown = asRecord(summary['majorHoldersBreakdown']);

    if (!price) {
      return buildUnavailableAnalysis({
        symbol,
        name: fallbackName,
        exchange: fallbackExchange,
        currency,
      });
    }

    const currentPrice = toNumber(price['regularMarketPrice']);

    if (typeof currentPrice !== 'number') {
      return buildUnavailableAnalysis({
        symbol,
        name: fallbackName,
        exchange: fallbackExchange,
        currency,
      });
    }

    // Data Extraction
    const openPrice = toNumber(price['regularMarketOpen']) ?? currentPrice;
    const high52 =
      toNumber(defaultKeyStatistics?.['fiftyTwoWeekHigh']) ??
      toNumber(price['regularMarketDayHigh']) ??
      currentPrice;
    const low52 =
      toNumber(defaultKeyStatistics?.['fiftyTwoWeekLow']) ??
      toNumber(price['regularMarketDayLow']) ??
      currentPrice;
    const rFactor = calculateRFactor(currentPrice, low52, high52);

    const insiderBuyPercent = toNumber(netSharePurchaseActivity?.['netPercentInsiderShares']) ?? 0;
    const instHeld = toNumber(majorHoldersBreakdown?.['institutionsPercentHeld']) ?? 0;
    const changePercent = toNumber(price['regularMarketChangePercent']) ?? 0;

    const volume = toNumber(price['regularMarketVolume']) ?? 0;
    const avgVolume =
      toNumber(price['averageDailyVolume10Day']) ??
      toNumber(price['averageDailyVolume3Month']) ??
      volume;
    const volSpike = avgVolume > 0 ? volume / avgVolume : 1;

    // Get Market Cap
    const marketCap = toNumber(price['marketCap']) ?? 0;

    // Calculate Intraday Trend (with 0.1% buffer to avoid noise)
    const intradayBuffer = openPrice * 0.001;
    const intradayTrend: IntradayTrend = currentPrice > openPrice + intradayBuffer ? 'Bullish' : 'Bearish';

    const { score, reasons, signal } = computeStrongMoney({
      insiderBuyPercent,
      instHeld,
      rFactor,
      volSpike,
      intradayTrend,
    });

    return {
      symbol: stripYahooSuffix(symbol),
      name:
        typeof price['shortName'] === 'string' && price['shortName'].trim()
          ? price['shortName']
          : fallbackName,
      sector: normalizeSector(summaryProfile?.['sector']),
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
      marketCap,
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

  // Filter out stocks where quote data wasn't available.
  // These are represented by the fallback sector "Data Unavailable".
  // Keep the full analyzed count for observability, but do not render unavailable stocks.
  const stocksWithData = analyzedStocks.filter((s) => {
    if (s.sector === 'Data Unavailable') return false;
    if (!Number.isFinite(s.price) || s.price <= 0) return false;
    if (!Number.isFinite(s.openPrice) || s.openPrice <= 0) return false;
    if (!Number.isFinite(s.changePercent)) return false;
    return true;
  });

  // Group by Sector
  const sectorMap = new Map<string, StockAnalysis[]>();
  stocksWithData.forEach((stock) => {
    const existing = sectorMap.get(stock.sector) ?? [];
    existing.push(stock);
    sectorMap.set(stock.sector, existing);
  });

  // Build Heatmap Data and Sector Scopes
  const heatmap: SectorHeatmapData[] = [];
  const sectors: SectorScope[] = [];

  // Track overall market A/D
  let marketAdvancing = 0;
  let marketDeclining = 0;

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

    // Calculate A/D Ratio for sector
    // Advancing: stocks with changePercent > 0
    // Declining: stocks with changePercent < 0
    const advancingStocks = sectorStocks.filter((s) => s.changePercent > 0).length;
    const decliningStocks = sectorStocks.filter((s) => s.changePercent < 0).length;
    
    // Update market totals
    marketAdvancing += advancingStocks;
    marketDeclining += decliningStocks;

    // A/D Ratio: Advancing / Declining (handle division by zero)
    let adRatio = 1;
    if (decliningStocks > 0) {
      adRatio = Number.parseFloat((advancingStocks / decliningStocks).toFixed(2));
    } else if (advancingStocks > 0) {
      adRatio = 999;
    }

    // Calculate Market Cap weighted % Change
    // Formula: Σ(Stock % Change × Market Cap) / Σ Market Cap
    let totalMarketCap = 0;
    let weightedChangeSum = 0;
    
    for (const stock of sectorStocks) {
      const cap = stock.marketCap ?? 0;
      if (cap > 0) {
        totalMarketCap += cap;
        weightedChangeSum += stock.changePercent * cap;
      }
    }
    
    const weightedChangePercent = totalMarketCap > 0
      ? Number.parseFloat((weightedChangeSum / totalMarketCap).toFixed(2))
      : 0;

    // Calculate average R-Factor
    const avgRFactor = sectorStocks.reduce((sum, s) => sum + s.rFactor, 0) / sectorStocks.length;

    // Calculate Strong Money Intensity (-100 to +100)
    // Positive = more buying, Negative = more selling
    const totalScores = sectorStocks.reduce((sum, s) => sum + s.strongMoneyScore, 0);
    const maxPossibleScore = sectorStocks.length * 5; // Max score per stock is ~5
    const strongMoneyIntensity = maxPossibleScore > 0 ? (totalScores / maxPossibleScore) * 100 : 0;

    // Determine sector sentiment based on A/D Ratio
    // Ratio > 1.5 = Bullish, < 0.7 = Bearish, else Neutral
    let sentiment: 'Bullish' | 'Bearish' | 'Neutral' = 'Neutral';
    if (adRatio > 1.5) sentiment = 'Bullish';
    else if (adRatio < 0.7) sentiment = 'Bearish';

    const heatmapData: SectorHeatmapData = {
      sector,
      stockCount: sectorStocks.length,
      avgRFactor: Number.parseFloat(avgRFactor.toFixed(1)),
      strongMoneyIntensity: Number.parseFloat(strongMoneyIntensity.toFixed(1)),
      buyingStocks,
      sellingStocks,
      sentiment,
      weightedChangePercent,
      adRatio,
      advancingStocks,
      decliningStocks,
      totalMarketCap,
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

  // Sort heatmap by weighted change % (highest first)
  heatmap.sort((a, b) => b.weightedChangePercent - a.weightedChangePercent);

  // Sort sectors by weighted change % (strongest first)
  sectors.sort((a, b) => b.heatmapData.weightedChangePercent - a.heatmapData.weightedChangePercent);

  // Calculate overall market A/D Ratio and sentiment
  let marketADRatio = 1;
  if (marketDeclining > 0) {
    marketADRatio = Number.parseFloat((marketAdvancing / marketDeclining).toFixed(2));
  } else if (marketAdvancing > 0) {
    marketADRatio = 999;
  }
  
  let marketSentiment: 'Bullish' | 'Bearish' | 'Neutral' = 'Neutral';
  if (marketADRatio > 1.5) marketSentiment = 'Bullish';
  else if (marketADRatio < 0.7) marketSentiment = 'Bearish';

  return {
    market,
    heatmap,
    sectors,
    totalStocksAnalyzed: analyzedStocks.length,
    totalStocksWithData: stocksWithData.length,
    timestamp: new Date().toISOString(),
    marketADRatio,
    marketAdvancing,
    marketDeclining,
    marketSentiment,
  };
};
