'use client';

import Link from 'next/link';
import { useEffect, useState, useCallback } from 'react';
import {
  getStrongMoneyScope,
  type MarketScopeResult,
  type SectorHeatmapData,
  type SectorScope,
  type StockAnalysis,
} from '@/lib/actions/analysis.actions';
import { F_O_STOCKS } from '@/lib/constants';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import { Activity, TrendingUp, Building2, HelpCircle, AlertTriangle } from 'lucide-react';
import TradingLoader from '@/components/ui/TradingLoader';

type SentimentType = 'Bullish' | 'Bearish' | 'Neutral';

type StreamQuoteUpdate = {
  currentPrice: number;
  openPrice?: number;
  percentChange?: number;
};

type ScopeCachePayload = {
  timestamp: number;
  result: MarketScopeResult;
};

type SectorFlowModel = {
  scope: SectorScope;
  intensity: number;
  topBullish: StockAnalysis[];
  topBearish: StockAnalysis[];
  outflowBullish: StockAnalysis[];
};

const chunkArray = <T,>(items: T[], chunkSize: number): T[][] => {
  if (chunkSize <= 0) return [items];
  const out: T[][] = [];
  for (let i = 0; i < items.length; i += chunkSize) {
    out.push(items.slice(i, i + chunkSize));
  }
  return out;
};

const getIndiaTimeParts = () => {
  const parts = new Intl.DateTimeFormat('en-GB', {
    timeZone: 'Asia/Kolkata',
    weekday: 'short',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
  }).formatToParts(new Date());

  const getPart = (type: string): string => parts.find((p) => p.type === type)?.value ?? '';
  const weekday = getPart('weekday').toLowerCase();
  const hour = Number.parseInt(getPart('hour'), 10);
  const minute = Number.parseInt(getPart('minute'), 10);
  return { weekday, hour: Number.isFinite(hour) ? hour : 0, minute: Number.isFinite(minute) ? minute : 0 };
};

const isIndiaWeekday = () => {
  const { weekday } = getIndiaTimeParts();
  return weekday !== 'sat' && weekday !== 'sun';
};

const getIndiaMinuteOfDay = () => {
  const { hour, minute } = getIndiaTimeParts();
  return hour * 60 + minute;
};

const getScopeRefreshIntervalMs = () => {
  if (!isIndiaWeekday()) return 20 * 60 * 1000;

  const minuteOfDay = getIndiaMinuteOfDay();
  const preSessionStart = 9 * 60;
  const marketOpen = 9 * 60 + 15;
  const earlySessionEnd = 9 * 60 + 45;
  const marketClose = 15 * 60 + 30;

  if (minuteOfDay >= preSessionStart && minuteOfDay < marketOpen) return 60 * 1000;
  if (minuteOfDay >= marketOpen && minuteOfDay < earlySessionEnd) return 45 * 1000;
  if (minuteOfDay >= earlySessionEnd && minuteOfDay <= marketClose) return 3 * 60 * 1000;
  return 12 * 60 * 1000;
};

const getScopeCacheTtlMs = () => {
  if (!isIndiaWeekday()) return 4 * 60 * 60 * 1000;

  const minuteOfDay = getIndiaMinuteOfDay();
  const preSessionStart = 9 * 60;
  const earlySessionEnd = 9 * 60 + 45;
  const marketClose = 15 * 60 + 30;

  if (minuteOfDay >= preSessionStart && minuteOfDay < earlySessionEnd) return 90 * 1000;
  if (minuteOfDay >= earlySessionEnd && minuteOfDay <= marketClose) return 4 * 60 * 1000;
  return 45 * 60 * 1000;
};

const isIndiaMarketOpenWindow = () => {
  if (!isIndiaWeekday()) return false;
  const minuteOfDay = getIndiaMinuteOfDay();
  const preSessionStart = 9 * 60;
  const marketClose = 15 * 60 + 30;
  return minuteOfDay >= preSessionStart && minuteOfDay <= marketClose;
};

const getRecentDateKeys = (days: number): string[] => {
  const keys: string[] = [];
  const now = new Date();

  for (let i = 0; i < days; i += 1) {
    const d = new Date(now);
    d.setDate(now.getDate() - i);
    keys.push(d.toISOString().slice(0, 10));
  }

  return keys;
};

const toFiniteNumber = (v: unknown): number | undefined => {
  return typeof v === 'number' && Number.isFinite(v) ? v : undefined;
};

const buildQuoteUpdateMap = (
  quotes: Array<Record<string, unknown>>,
  canonicalSymbol: (symbol: string) => string
): Map<string, StreamQuoteUpdate> => {
  const map = new Map<string, StreamQuoteUpdate>();

  for (const q of quotes) {
    const rawSymbol = typeof q.symbol === 'string' ? q.symbol : '';
    const sym = canonicalSymbol(rawSymbol);
    if (!sym) continue;

    const currentPrice = toFiniteNumber(q.currentPrice);
    if (typeof currentPrice !== 'number') continue;

    const openPrice = toFiniteNumber(q.openPrice);
    const percentChange = toFiniteNumber(q.percentChange);
    map.set(sym, { currentPrice, openPrice, percentChange });
  }

  return map;
};

const applyQuoteUpdates = (args: {
  prev: MarketScopeResult;
  updates: Map<string, StreamQuoteUpdate>;
  canonicalSymbol: (symbol: string) => string;
}): MarketScopeResult => {
  const { prev, updates, canonicalSymbol } = args;
  const bullishBuffer = 0.001; // 0.1%

  const nextSectors = prev.sectors.map((sector) => {
    const nextStocks = sector.stocks.map((s) => {
      const key = canonicalSymbol(s.symbol);
      const u = updates.get(key);
      if (!u) return s;

      const nextPrice = u.currentPrice;
      const nextOpen = typeof u.openPrice === 'number' ? u.openPrice : s.openPrice;

      const computedChangePercent =
        Number.isFinite(nextOpen) && nextOpen !== 0 ? ((nextPrice - nextOpen) / nextOpen) * 100 : s.changePercent;
      const nextChangePercent = typeof u.percentChange === 'number' ? u.percentChange : computedChangePercent;

      const nextTrend: StockAnalysis['intradayTrend'] =
        nextPrice >= nextOpen * (1 - bullishBuffer) ? 'Bullish' : 'Bearish';

      return {
        ...s,
        price: nextPrice,
        openPrice: nextOpen,
        changePercent: nextChangePercent,
        intradayTrend: nextTrend,
      };
    });

    return { ...sector, stocks: nextStocks };
  });

  return { ...prev, sectors: nextSectors };
};

const pickUniqueBySymbol = (items: StockAnalysis[], limit: number): StockAnalysis[] => {
  const seen = new Set<string>();
  const out: StockAnalysis[] = [];

  for (const item of items) {
    const key = item.symbol.toUpperCase();
    if (seen.has(key)) continue;
    seen.add(key);
    out.push(item);
    if (out.length >= limit) break;
  }

  return out;
};

const bullishScore = (stock: StockAnalysis): number => {
  const signalBoost = stock.strongMoneySignal === 'Buying' ? 40 : 0;
  const moneyScore = Math.max(0, stock.strongMoneyScore) * 10;
  const trendBoost = stock.intradayTrend === 'Bullish' ? 8 : 0;
  return signalBoost + moneyScore + stock.rFactor + trendBoost;
};

const bearishScore = (stock: StockAnalysis): number => {
  const signalBoost = stock.strongMoneySignal === 'Selling' ? 40 : 0;
  const moneyScore = Math.max(0, -stock.strongMoneyScore) * 10;
  const trendBoost = stock.intradayTrend === 'Bearish' ? 8 : 0;
  return signalBoost + moneyScore + (100 - stock.rFactor) + trendBoost;
};

const buildSectorFlowModels = (result: MarketScopeResult): {
  topInflowSectors: SectorFlowModel[];
  topOutflowSectors: SectorFlowModel[];
} => {
  const intensityBySector = new Map(result.heatmap.map((h) => [h.sector, h.strongMoneyIntensity]));

  const sectorModels = result.sectors.map((scope) => {
    const sortedBullish = [...scope.stocks].sort((a, b) => bullishScore(b) - bullishScore(a));
    const sortedBearish = [...scope.stocks].sort((a, b) => bearishScore(b) - bearishScore(a));

    const bullishPrimary = sortedBullish.filter(
      (stock) => stock.strongMoneySignal === 'Buying' && stock.intradayTrend === 'Bullish'
    );
    const bearishPrimary = sortedBearish.filter(
      (stock) => stock.strongMoneySignal === 'Selling' && stock.intradayTrend === 'Bearish'
    );

    const topBullish = pickUniqueBySymbol([...bullishPrimary, ...sortedBullish], 10);
    const topBearish = pickUniqueBySymbol([...bearishPrimary, ...sortedBearish], 10);
    const outflowBullish = pickUniqueBySymbol(
      sortedBullish.filter(
        (stock) => stock.strongMoneySignal === 'Buying' || stock.intradayTrend === 'Bullish' || stock.rFactor >= 60
      ),
      5
    );

    return {
      scope,
      intensity: intensityBySector.get(scope.sector) ?? 0,
      topBullish,
      topBearish,
      outflowBullish,
    };
  });

  const topInflowSectors = [...sectorModels]
    .sort((a, b) => b.intensity - a.intensity)
    .slice(0, 3);

  const topOutflowSectors = [...sectorModels]
    .sort((a, b) => a.intensity - b.intensity)
    .slice(0, 3);

  return { topInflowSectors, topOutflowSectors };
};

function FlowStocksTable({
  stocks,
  type,
}: Readonly<{
  stocks: StockAnalysis[];
  type: 'bullish' | 'bearish';
}>) {
  const symbolColor = type === 'bullish' ? 'text-green-400' : 'text-red-400';
  const badgeClass =
    type === 'bullish'
      ? 'border-green-500/40 text-green-400 bg-green-500/10'
      : 'border-red-500/40 text-red-400 bg-red-500/10';

  if (stocks.length === 0) {
    return <p className="text-xs text-muted-foreground">No stocks available for this bucket.</p>;
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-xs">
        <thead>
          <tr className="border-b border-border/30 text-muted-foreground uppercase tracking-wider">
            <th className="py-2 text-left font-semibold">Symbol</th>
            <th className="py-2 text-right font-semibold">Signal</th>
            <th className="py-2 text-right font-semibold">R</th>
            <th className="py-2 text-right font-semibold">Trend</th>
          </tr>
        </thead>
        <tbody>
          {stocks.map((stock) => (
            <tr key={`${type}-${stock.symbol}`} className="border-b border-border/20 hover:bg-muted/20">
              <td className={`py-2 font-mono font-semibold ${symbolColor}`}>
                <Link href={`/simulator/${stock.symbol}`}>{stock.symbol}</Link>
              </td>
              <td className="py-2 text-right">
                <Badge variant="outline" className={badgeClass}>
                  {stock.strongMoneySignal}
                </Badge>
              </td>
              <td className="py-2 text-right font-semibold text-yellow-500">{stock.rFactor.toFixed(0)}</td>
              <td className={`py-2 text-right font-semibold ${stock.intradayTrend === 'Bullish' ? 'text-green-400' : 'text-red-400'}`}>
                {stock.intradayTrend}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// Helper function to get A/D Ratio badge style
const getADRatioStyle = (sentiment: SentimentType): string => {
  if (sentiment === 'Bullish') return 'border-green-500/50 text-green-500 bg-green-500/10';
  if (sentiment === 'Bearish') return 'border-red-500/50 text-red-500 bg-red-500/10';
  return 'border-muted text-muted-foreground';
};

// Helper function to get sentiment badge variant
const getSentimentBadgeVariant = (sentiment: SentimentType): 'default' | 'destructive' | 'secondary' => {
  if (sentiment === 'Bullish') return 'default';
  if (sentiment === 'Bearish') return 'destructive';
  return 'secondary';
};

// ============================================================================
// STRATEGY GUIDE MODAL
// ============================================================================

function StrategyGuide() {
  return (
    <Dialog>
      <DialogTrigger asChild>
        <button className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-yellow-500/10 border border-yellow-500/30 text-yellow-500 hover:bg-yellow-500/20 transition-colors text-sm font-medium">
          <HelpCircle className="h-4 w-4" />
          How to use this?
        </button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-md border-yellow-500/30 bg-background/95 backdrop-blur-sm">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2 text-yellow-500">
            <Activity className="h-5 w-5" />
            3-Step Safe Entry Strategy (F&O Edition)
          </DialogTitle>
          <DialogDescription className="text-muted-foreground">
            Use sector heatmaps and R-Factor rankings to identify strong stocks for derivatives trading.
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-4 mt-4">
          <div className="flex gap-3 p-3 rounded-lg bg-muted/30 border border-border/50">
            <div className="shrink-0 w-8 h-8 rounded-full bg-yellow-500/20 flex items-center justify-center text-yellow-500 font-bold">
              1
            </div>
            <div>
              <h4 className="font-semibold text-sm">Check Sector Heatmap</h4>
              <p className="text-xs text-muted-foreground mt-1">
                Look at the heatmap. <span className="text-green-500">Green sectors</span> have strong inflow. <span className="text-red-500">Red sectors</span> are seeing outflows.
              </p>
            </div>
          </div>

          <div className="flex gap-3 p-3 rounded-lg bg-muted/30 border border-border/50">
            <div className="shrink-0 w-8 h-8 rounded-full bg-yellow-500/20 flex items-center justify-center text-yellow-500 font-bold">
              2
            </div>
            <div>
              <h4 className="font-semibold text-sm">Pick F&O Eligible Leaders</h4>
              <p className="text-xs text-muted-foreground mt-1">
                This panel shows only F&O eligible stocks. Look for <span className="text-green-500">R-Factor &gt; 80</span> leaders with strong momentum.
              </p>
            </div>
          </div>

          <div className="flex gap-3 p-3 rounded-lg bg-muted/30 border border-border/50">
            <div className="shrink-0 w-8 h-8 rounded-full bg-yellow-500/20 flex items-center justify-center text-yellow-500 font-bold">
              3
            </div>
            <div>
              <h4 className="font-semibold text-sm text-yellow-500">⚠️ Check Intraday Trend</h4>
              <p className="text-xs text-muted-foreground mt-1">
                <span className="text-green-500 font-medium">🟢 Bullish Today</span> = Better risk/reward for options premiums.
                <br/>
                <span className="text-red-500 font-medium">🔴 Profit Booking</span> = Wait for reversal.
              </p>
            </div>
          </div>

          <div className="p-3 rounded-lg bg-yellow-500/10 border border-yellow-500/30">
            <p className="text-xs text-yellow-600 dark:text-yellow-400">
              <strong>Pro Tip:</strong> F&O stocks in green sectors with high R-Factor provide the best options trading opportunities.
            </p>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}

// ============================================================================
// HEATMAP COMPONENT
// ============================================================================

type SectorHeatmapProps = Readonly<{
  data: SectorHeatmapData[];
  onSectorClick?: (sector: string) => void;
}>;

function SectorHeatmap({ data, onSectorClick }: SectorHeatmapProps) {
  const sorted = [...data].sort((a, b) => b.strongMoneyIntensity - a.strongMoneyIntensity);

  const getBgColor = (sentiment: SentimentType, isNeutral: boolean): string => {
    if (sentiment === 'Bullish') return 'bg-green-500/20 hover:bg-green-500/30';
    if (isNeutral) return 'bg-muted/40 hover:bg-muted/50';
    return 'bg-red-500/20 hover:bg-red-500/30';
  };

  const getTextColor = (sentiment: SentimentType, isNeutral: boolean): string => {
    if (sentiment === 'Bullish') return 'text-green-400';
    if (isNeutral) return 'text-muted-foreground';
    return 'text-red-400';
  };

  const getBorderColor = (sentiment: SentimentType, isNeutral: boolean): string => {
    if (sentiment === 'Bullish') return 'border-green-500/40';
    if (isNeutral) return 'border-muted';
    return 'border-red-500/40';
  };

  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3">
      {sorted.map((sector) => {
        const isNeutral = sector.sentiment === 'Neutral';
        const bgColor = getBgColor(sector.sentiment, isNeutral);
        const textColor = getTextColor(sector.sentiment, isNeutral);
        const borderColor = getBorderColor(sector.sentiment, isNeutral);

        return (
          <button
            key={sector.sector}
            className={`p-3 rounded-lg border cursor-pointer transition-all ${bgColor} ${borderColor} text-left hover:shadow-md`}
            onClick={() => onSectorClick?.(sector.sector)}
            type="button"
          >
            <div className={`font-semibold text-sm ${textColor} truncate`}>{sector.sector}</div>
            <div className="text-xs text-muted-foreground mt-1">
              {sector.buyingStocks} Buying • {sector.sellingStocks} Selling
            </div>
            <div className="text-xs text-muted-foreground">
              {sector.stockCount} stocks • Avg R: {sector.avgRFactor.toFixed(0)}
            </div>
          </button>
        );
      })}
    </div>
  );
}

// ============================================================================
// SECTOR DETAIL COMPONENT
// ============================================================================

type SectorDetailProps = Readonly<{
  scope: SectorScope;
  id?: string;
  currencySymbol: string;
}>;

function SectorDetail({ scope, id, currencySymbol }: SectorDetailProps) {
  const bullishStocks = scope.stocks.filter((s) => s.intradayTrend === 'Bullish');
  const bearishStocks = scope.stocks.filter((s) => s.intradayTrend === 'Bearish');

  return (
    <div
      id={id}
      className="rounded-lg border border-border/50 bg-muted/10 overflow-hidden"
      key={scope.sector}
    >
      {/* Sector Header */}
      <div className="bg-muted/20 px-4 py-3 border-b border-border/30">
        <div className="flex items-center justify-between mb-2">
          <h4 className="font-semibold flex items-center gap-2">
            <TrendingUp className="h-4 w-4 text-yellow-500" />
            {scope.sector}
          </h4>
          <Badge variant={getSentimentBadgeVariant(scope.sentiment)}>{scope.sentiment}</Badge>
        </div>
        <div className="flex flex-wrap gap-3 text-xs text-muted-foreground">
          <div>
            <span className="text-foreground font-semibold">{scope.stocks.length}</span> stocks
          </div>
          <div>
            <span className="text-green-500 font-semibold">{bullishStocks.length}</span> bullish today
          </div>
          <div>
            <span className="text-red-500 font-semibold">{bearishStocks.length}</span> profit booking
          </div>
          <div>
            Avg R: <span className="text-yellow-500 font-semibold">{
              scope.stocks.length > 0 
                ? (scope.stocks.reduce((sum, s) => sum + s.rFactor, 0) / scope.stocks.length).toFixed(0)
                : '0'
            }</span>
          </div>
        </div>
      </div>

      {/* Stocks Table */}
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border/30 text-muted-foreground text-xs uppercase tracking-wider bg-muted/30">
              <th className="px-3 py-2 text-left font-semibold">Symbol</th>
              <th className="px-3 py-2 text-right font-semibold">Price</th>
              <th className="px-3 py-2 text-right font-semibold">Trend</th>
              <th className="px-3 py-2 text-right font-semibold">R-Factor</th>
              <th className="px-3 py-2 text-center font-semibold">Signal</th>
            </tr>
          </thead>
          <tbody>
            {scope.stocks.map((stock) => {
              const isBullish = stock.intradayTrend === 'Bullish';
              const signalColorMap: Record<string, string> = {
                Buying: 'text-green-500',
                Selling: 'text-red-500',
                Neutral: 'text-muted-foreground',
              };
              const signalColor = signalColorMap[stock.strongMoneySignal] || 'text-muted-foreground';

              return (
                <tr
                  key={stock.symbol}
                  className="border-b border-border/20 hover:bg-muted/20 transition-colors cursor-pointer"
                >
                  <td className="px-3 py-2 font-mono font-bold text-cyan-400">
                    <Link href={`/simulator/${stock.symbol}`}>{stock.symbol}</Link>
                  </td>
                  <td className="px-3 py-2 text-right font-mono">
                    {currencySymbol}
                    {stock.price.toLocaleString(undefined, { maximumFractionDigits: 2 })}
                  </td>
                  <td className={`px-3 py-2 text-right font-bold ${isBullish ? 'text-green-500' : 'text-red-500'}`}>
                    {isBullish ? '🟢' : '🔴'} {isBullish ? 'Bullish' : 'Selling'}
                  </td>
                  <td className="px-3 py-2 text-right">
                    <Progress value={stock.rFactor} className="h-2" />
                    <span className="text-xs text-muted-foreground">{stock.rFactor.toFixed(0)}</span>
                  </td>
                  <td className={`px-3 py-2 text-center font-semibold ${signalColor}`}>{stock.strongMoneySignal}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// ============================================================================
// OPTIONS SCOPE PANEL COMPONENT
// ============================================================================

/**
 * OptionsScopePanel Component
 *
 * Specialized variant of MarketScopePanel tailored for F&O (Futures & Options) stocks.
 * Displays:
 * - Sector heatmap for F&O eligible stocks
 * - R-Factor rankings and momentum analysis
 * - Real-time price updates via SSE
 * - Intraday trend indicators
 *
 * This panel is exclusively for the Indian market (F&O is primarily traded on NSE).
 */
export default function OptionsScopePanel() {
  const [data, setData] = useState<MarketScopeResult | null>(null);
  const [streamItems, setStreamItems] = useState<Array<{ symbol: string; exchange?: string }>>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const currencySymbol = '₹'; // F&O is exclusively Indian (INR)
  const sectorFlows = data ? buildSectorFlowModels(data) : { topInflowSectors: [], topOutflowSectors: [] };

  const canonicalSymbol = useCallback((symbol: string): string => {
    const raw = String(symbol ?? '').trim();
    if (!raw) return '';

    // Remove exchange prefixes like "BSE:" or "NASDAQ:"
    const noPrefix = raw.includes(':') ? raw.split(':').pop() ?? raw : raw;
    const upper = noPrefix.toUpperCase();

    // Remove Yahoo-style Indian suffixes (we keep them for display, but stream wants base)
    if (upper.endsWith('.BO')) return upper.slice(0, -3);
    if (upper.endsWith('.NS')) return upper.slice(0, -3);
    return upper;
  }, []);

  const getCacheKeyForDate = useCallback((dateKey: string) => {
    return `mp.optionsScope.IN.${dateKey}`;
  }, []);

  const getCacheKey = useCallback(() => {
    const today = new Date().toISOString().slice(0, 10);
    return getCacheKeyForDate(today);
  }, [getCacheKeyForDate]);

  const computeStreamItems = useCallback((result: MarketScopeResult) => {
    const items: Array<{ symbol: string; exchange?: string }> = [];
    const seen = new Set<string>();

    for (const sector of result.sectors) {
      for (const stock of sector.stocks) {
        const sym = stock.symbol.toUpperCase();
        const exchange = stock.exchange ?? 'BSE';
        const key = `${sym}:${exchange}`;

        if (seen.has(key)) continue;
        seen.add(key);
        items.push({ symbol: sym, exchange });
      }
    }

    return items;
  }, []);

  const fetchData = useCallback(async (args?: { silent?: boolean }) => {
    const silent = Boolean(args?.silent);
    if (!silent) setLoading(true);
    setError(null);
    try {
      // Fetch full F&O universe for Indian market (avoid small per-sector cap)
      const result = await getStrongMoneyScope('IN', 500, F_O_STOCKS);

      // Filter to only F&O stocks
      const foSymbols = new Set(F_O_STOCKS.map((s) => canonicalSymbol(s.symbol)));

      const filteredSectors = result.sectors
        .map((sector) => ({
          ...sector,
          stocks: sector.stocks.filter((stock) => foSymbols.has(canonicalSymbol(stock.symbol))),
        }))
        .filter((sector) => sector.stocks.length > 0);

      const filteredStocksCount = filteredSectors.reduce((sum, s) => sum + s.stocks.length, 0);

      const filteredResult: MarketScopeResult = {
        ...result,
        sectors: filteredSectors,
        totalStocksAnalyzed: filteredStocksCount,
        totalStocksWithData: filteredStocksCount,
      };

      setData(filteredResult);
      setStreamItems(computeStreamItems(filteredResult));

      try {
        const payload: ScopeCachePayload = {
          timestamp: Date.now(),
          result: filteredResult,
        };
        localStorage.setItem(getCacheKey(), JSON.stringify(payload));
      } catch {
        /* ignore cache errors */
      }
    } catch (err) {
      console.error('Failed to fetch F&O market scope', err);
      setError('Failed to load F&O market data. Please try again.');
    } finally {
      if (!silent) setLoading(false);
    }
  }, [canonicalSymbol, computeStreamItems, getCacheKey]);

  const readFreshCache = useCallback((): boolean => {
    try {
      const cachedRaw = localStorage.getItem(getCacheKey());
      if (!cachedRaw) return false;

      const parsed = JSON.parse(cachedRaw) as ScopeCachePayload;
      if (!parsed || typeof parsed !== 'object') return false;
      if (typeof parsed.timestamp !== 'number') return false;
      if (!parsed.result || typeof parsed.result !== 'object') return false;
      if (Date.now() - parsed.timestamp > getScopeCacheTtlMs()) return false;

      setData(parsed.result);
      setStreamItems(computeStreamItems(parsed.result));
      setLoading(false);
      return true;
    } catch {
      return false;
    }
  }, [computeStreamItems, getCacheKey]);

  const readRecentCacheFallback = useCallback((): boolean => {
    try {
      const dateKeys = getRecentDateKeys(7);
      const today = new Date().toISOString().slice(0, 10);

      for (const dateKey of dateKeys) {
        if (dateKey === today) continue;

        const raw = localStorage.getItem(getCacheKeyForDate(dateKey));
        if (!raw) continue;

        const parsed = JSON.parse(raw) as ScopeCachePayload;
        if (!parsed || typeof parsed !== 'object') continue;
        if (!parsed.result || typeof parsed.result !== 'object') continue;

        setData(parsed.result);
        setStreamItems(computeStreamItems(parsed.result));
        setLoading(false);
        return true;
      }
    } catch {
      return false;
    }

    return false;
  }, [computeStreamItems, getCacheKeyForDate]);

  useEffect(() => {
    const hasFreshCache = readFreshCache();
    const canUseFallback = !isIndiaMarketOpenWindow();
    const hasFallbackCache = !hasFreshCache && canUseFallback ? readRecentCacheFallback() : false;
    const hasAnyCache = hasFreshCache || hasFallbackCache;
    fetchData({ silent: hasAnyCache });
  }, [fetchData, readFreshCache, readRecentCacheFallback]);

  useEffect(() => {
    let cancelled = false;
    let timer: ReturnType<typeof setTimeout> | undefined;

    const schedule = () => {
      if (cancelled) return;
      const nextMs = getScopeRefreshIntervalMs();
      timer = setTimeout(() => {
        if (cancelled) return;
        if (typeof document !== 'undefined' && document.visibilityState === 'hidden') {
          schedule();
          return;
        }

        fetchData({ silent: true }).finally(schedule);
      }, nextMs);
    };

    schedule();

    return () => {
      cancelled = true;
      if (timer) clearTimeout(timer);
    };
  }, [fetchData]);

  const applyStreamQuotes = useCallback((quotes: Array<Record<string, unknown>>) => {
    const updates = buildQuoteUpdateMap(quotes, canonicalSymbol);
    if (updates.size === 0) return;

    setData((prev) => {
      if (!prev) return prev;
      return applyQuoteUpdates({ prev, updates, canonicalSymbol });
    });
  }, [canonicalSymbol]);

  // Real-time price updates via SSE
  useEffect(() => {
    if (loading) return;
    if (error) return;
    if (streamItems.length === 0) return;
    if (globalThis.window === undefined) return;
    if (typeof EventSource === 'undefined') return;

    let cancelled = false;
    const sources: EventSource[] = [];

    const chunks = chunkArray(streamItems, 50);

    const computeRetryDelayMs = (retryAttempt: number): number => {
      const baseDelayMs = 1_500;
      const maxDelayMs = 15_000;
      const jitterMs = Math.floor(Math.random() * 400);
      return Math.min(maxDelayMs, baseDelayMs * Math.pow(1.6, retryAttempt)) + jitterMs;
    };

    function retryLater(items: Array<{ symbol: string; exchange?: string }>, retryAttempt: number): void {
      if (cancelled) return;
      startChunkStream(items, retryAttempt);
    }

    function startChunkStream(items: Array<{ symbol: string; exchange?: string }>, retryAttempt: number = 0): void {
      const url = `/api/quotes/stream?items=${encodeURIComponent(JSON.stringify(items))}`;
      const es = new EventSource(url);
      sources.push(es);

      const retry = () => {
        es.close();
        if (cancelled) return;

        const nextDelay = computeRetryDelayMs(retryAttempt);
        globalThis.setTimeout(retryLater, nextDelay, items, retryAttempt + 1);
      };

      es.addEventListener('quotes', (evt) => {
        if (cancelled) return;
        try {
          const payload = JSON.parse((evt as MessageEvent<string>).data) as { quotes?: unknown };
          if (Array.isArray(payload.quotes)) {
            applyStreamQuotes(payload.quotes);
          }
        } catch (e) {
          console.error('Failed to parse quotes', e);
        }
      });

      es.addEventListener('error', retry);
      es.onerror = retry;
    }

    chunks.forEach((chunk) => {
      startChunkStream(chunk);
    });

    return () => {
      cancelled = true;
      sources.forEach((s) => s.close());
    };
  }, [loading, error, streamItems, applyStreamQuotes]);

  if (loading) {
    return (
      <div className="flex items-center justify-center p-8">
        <TradingLoader />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <Card className="bg-background/50 border-yellow-500/20">
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between mb-4">
            <CardTitle className="flex items-center gap-2 text-yellow-500">
              <Building2 className="h-5 w-5" />
              F&O Market Scope — Sector Heatmap & Institutional Money Flow
            </CardTitle>
            <StrategyGuide />
          </div>
        </CardHeader>

        <CardContent className="space-y-6">
          {/* Error State */}
          {error && (
            <div className="flex items-start gap-3 p-4 rounded-lg bg-red-500/5 border border-red-500/20">
              <AlertTriangle className="h-5 w-5 text-red-500 mt-0.5" />
              <div className="text-sm">
                <p className="font-medium text-red-500">{error}</p>
                <button onClick={() => { void fetchData(); }} className="text-xs text-red-400 hover:text-red-300 mt-2 underline">
                  Try again
                </button>
              </div>
            </div>
          )}

          {/* Data Display */}
          {!error && data && (
            <>
              {/* Stats Bar */}
              <div className="flex flex-wrap gap-4 p-4 rounded-lg bg-yellow-500/5 border border-yellow-500/20">
                <div className="text-sm">
                  <span className="text-muted-foreground">F&O Universe:</span>{' '}
                  <span className="font-semibold text-yellow-500">{F_O_STOCKS.length}</span>
                </div>
                <div className="text-sm">
                  <span className="text-muted-foreground">Fetched With Data:</span>{' '}
                  <span className="font-semibold text-yellow-500">{data.totalStocksWithData}</span>
                </div>
                <div className="text-sm">
                  <span className="text-muted-foreground">Active Sectors:</span>{' '}
                  <span className="font-semibold text-yellow-500">{data.sectors.length}</span>
                </div>
                <div className="text-sm">
                  <span className="text-muted-foreground">A/D Ratio:</span>{' '}
                  <Badge variant="outline" className={`font-mono font-bold ${getADRatioStyle(data.marketSentiment)}`}>
                    {data.marketADRatio >= 999 ? '∞' : data.marketADRatio.toFixed(2)}
                  </Badge>
                </div>
                <div className="text-sm">
                  <span className="text-muted-foreground">Last Updated:</span>{' '}
                  <span className="font-semibold">{new Date(data.timestamp).toLocaleTimeString()}</span>
                </div>
              </div>

              {/* Heatmap */}
              {data.heatmap.length > 0 && <SectorHeatmap data={data.heatmap} />}

              {/* Sector-first Institutional Flow View */}
              <div className="space-y-4">
                <h3 className="text-lg font-semibold flex items-center gap-2">
                  <TrendingUp className="h-5 w-5 text-yellow-500" />
                  Institutional Flow by Sector
                </h3>

                <div className="space-y-4">
                  <h4 className="text-sm font-semibold text-green-400">Money Inflow Sectors (Institutions Buying)</h4>
                  {sectorFlows.topInflowSectors.length === 0 ? (
                    <p className="text-sm text-muted-foreground">No inflow sectors detected right now.</p>
                  ) : (
                    <div className="grid grid-cols-1 xl:grid-cols-3 gap-4">
                      {sectorFlows.topInflowSectors.map((flow) => (
                        <Card key={`inflow-${flow.scope.sector}`} className="border-green-500/30 bg-green-500/5">
                          <CardHeader className="pb-2">
                            <CardTitle className="text-sm flex items-center justify-between gap-2">
                              <span className="text-green-400 truncate">{flow.scope.sector}</span>
                              <Badge variant="outline" className="border-green-500/40 text-green-400 bg-green-500/10">
                                {flow.intensity.toFixed(1)}
                              </Badge>
                            </CardTitle>
                            <p className="text-xs text-muted-foreground">Top 10 Bullish Stocks (Institutional Buying)</p>
                          </CardHeader>
                          <CardContent>
                            <FlowStocksTable stocks={flow.topBullish} type="bullish" />
                          </CardContent>
                        </Card>
                      ))}
                    </div>
                  )}
                </div>

                <div className="space-y-4">
                  <h4 className="text-sm font-semibold text-red-400">Money Outflow Sectors (Institutions Selling)</h4>
                  {sectorFlows.topOutflowSectors.length === 0 ? (
                    <p className="text-sm text-muted-foreground">No outflow sectors detected right now.</p>
                  ) : (
                    <div className="grid grid-cols-1 xl:grid-cols-3 gap-4">
                      {sectorFlows.topOutflowSectors.map((flow) => (
                        <Card key={`outflow-${flow.scope.sector}`} className="border-red-500/30 bg-red-500/5">
                          <CardHeader className="pb-2">
                            <CardTitle className="text-sm flex items-center justify-between gap-2">
                              <span className="text-red-400 truncate">{flow.scope.sector}</span>
                              <Badge variant="outline" className="border-red-500/40 text-red-400 bg-red-500/10">
                                {flow.intensity.toFixed(1)}
                              </Badge>
                            </CardTitle>
                            <p className="text-xs text-muted-foreground">Top 10 Bearish + Top 5 Bullish (same sector)</p>
                          </CardHeader>
                          <CardContent className="space-y-4">
                            <div>
                              <p className="text-xs font-semibold text-red-400 mb-2">Top 10 Bearish (Institutional Selling)</p>
                              <FlowStocksTable stocks={flow.topBearish} type="bearish" />
                            </div>
                            <div>
                              <p className="text-xs font-semibold text-green-400 mb-2">Top 5 Bullish (relative strength inside weak sector)</p>
                              <FlowStocksTable stocks={flow.outflowBullish} type="bullish" />
                            </div>
                          </CardContent>
                        </Card>
                      ))}
                    </div>
                  )}
                </div>
              </div>

              {/* Detailed Sector Analysis */}
              <div className="space-y-4">
                <h3 className="text-lg font-semibold flex items-center gap-2">
                  <TrendingUp className="h-5 w-5 text-yellow-500" />
                  Detailed F&O Sector Analysis
                  <span className="text-xs text-muted-foreground font-normal ml-2">
                    (Bullish Today first, then by R-Factor)
                  </span>
                </h3>

                {data.sectors.length === 0 ? (
                  <p className="text-muted-foreground text-center py-6">
                    No F&O sectors/stocks to display.
                  </p>
                ) : (
                  <div className="space-y-6">
                    {data.sectors.map((scope) => (
                      <SectorDetail
                        key={scope.sector}
                        scope={scope}
                        id={`sector-${scope.sector.replaceAll(/\s+/g, '-').toLowerCase()}`}
                        currencySymbol={currencySymbol}
                      />
                    ))}
                  </div>
                )}
              </div>
            </>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
