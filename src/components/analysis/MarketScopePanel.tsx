'use client';

import Link from 'next/link';
import { useEffect, useMemo, useState, useCallback } from 'react';
import {
  getStrongMoneyScope,
  type MarketScopeResult,
  type SectorHeatmapData,
  type SectorScope,
  type StockAnalysis,
} from '@/lib/actions/analysis.actions';
import type { MarketType } from '@/lib/constants';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Progress } from '@/components/ui/progress';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import { Activity, TrendingUp, TrendingDown, Globe, Building2, HelpCircle, CheckCircle2, AlertTriangle, Zap } from 'lucide-react';
import TradingLoader from '@/components/ui/TradingLoader';

type SentimentType = 'Bullish' | 'Bearish' | 'Neutral';

type StreamQuoteUpdate = {
  currentPrice: number;
  openPrice?: number;
  percentChange?: number;
};

const chunkArray = <T,>(items: T[], chunkSize: number): T[][] => {
  if (chunkSize <= 0) return [items];
  const out: T[][] = [];
  for (let i = 0; i < items.length; i += chunkSize) {
    out.push(items.slice(i, i + chunkSize));
  }
  return out;
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
            3-Step Safe Entry Strategy
          </DialogTitle>
          <DialogDescription className="text-muted-foreground">
            Follow these steps to avoid buying strong stocks on bad days.
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-4 mt-4">
          <div className="flex gap-3 p-3 rounded-lg bg-muted/30 border border-border/50">
            <div className="shrink-0 w-8 h-8 rounded-full bg-yellow-500/20 flex items-center justify-center text-yellow-500 font-bold">
              1
            </div>
            <div>
              <h4 className="font-semibold text-sm">Check Sector Color</h4>
              <p className="text-xs text-muted-foreground mt-1">
                Look at the heatmap. <span className="text-green-500">Green sectors</span> have strong money inflow. <span className="text-red-500">Red sectors</span> are seeing outflows.
              </p>
            </div>
          </div>

          <div className="flex gap-3 p-3 rounded-lg bg-muted/30 border border-border/50">
            <div className="shrink-0 w-8 h-8 rounded-full bg-yellow-500/20 flex items-center justify-center text-yellow-500 font-bold">
              2
            </div>
            <div>
              <h4 className="font-semibold text-sm">Pick High R-Factor Leaders</h4>
              <p className="text-xs text-muted-foreground mt-1">
                Stocks with <span className="text-green-500">R-Factor &gt; 80</span> are near 52-week highs.
                These are the sector leaders with strong momentum.
              </p>
            </div>
          </div>

          <div className="flex gap-3 p-3 rounded-lg bg-muted/30 border border-border/50">
            <div className="shrink-0 w-8 h-8 rounded-full bg-yellow-500/20 flex items-center justify-center text-yellow-500 font-bold">
              3
            </div>
            <div>
              <h4 className="font-semibold text-sm text-yellow-500">⚠️ CRITICAL: Check Intraday Trend</h4>
              <p className="text-xs text-muted-foreground mt-1">
                <span className="text-green-500 font-medium">🟢 Bullish Today</span> = Safe to enter (Price &gt; Open).<br/>
                <span className="text-red-500 font-medium">🔴 Profit Booking</span> = WAIT! Stock is falling today.
              </p>
            </div>
          </div>

          <div className="p-3 rounded-lg bg-yellow-500/10 border border-yellow-500/30">
            <p className="text-xs text-yellow-600 dark:text-yellow-400">
              <strong>Pro Tip:</strong> Never buy a strong stock on a red day. Wait for the next green day to enter.
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

interface SectorHeatmapProps {
  data: SectorHeatmapData[];
  onSectorClick: (sector: string) => void;
}

function SectorHeatmap({ data, onSectorClick }: Readonly<SectorHeatmapProps>) {
  // Get color based on Strong Money Intensity
  const getHeatColor = (intensity: number): string => {
    if (intensity >= 40) return 'bg-green-500/90 hover:bg-green-500 text-white';
    if (intensity >= 20) return 'bg-green-500/60 hover:bg-green-500/80 text-white';
    if (intensity >= 5) return 'bg-green-500/30 hover:bg-green-500/50 text-green-100';
    if (intensity <= -40) return 'bg-red-500/90 hover:bg-red-500 text-white';
    if (intensity <= -20) return 'bg-red-500/60 hover:bg-red-500/80 text-white';
    if (intensity <= -5) return 'bg-red-500/30 hover:bg-red-500/50 text-red-100';
    // Neutral: keep it subtle gray (default)
    return 'bg-muted/40 hover:bg-muted/60 text-foreground';
  };

  // Get border style based on sentiment
  const getBorderStyle = (sentiment: SentimentType): string => {
    if (sentiment === 'Bullish') return 'border-green-500/50';
    if (sentiment === 'Bearish') return 'border-red-500/50';
    return 'border-border/60';
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold flex items-center gap-2">
          <Activity className="h-5 w-5 text-yellow-500" />
          Sector Heatmap
        </h3>
        <div className="flex items-center gap-4 text-xs">
          <div className="flex items-center gap-1">
            <div className="w-3 h-3 rounded bg-green-500/90" />
            <span className="text-muted-foreground">Strong Buying</span>
          </div>
          <div className="flex items-center gap-1">
            <div className="w-3 h-3 rounded bg-muted/70" />
            <span className="text-muted-foreground">Neutral</span>
          </div>
          <div className="flex items-center gap-1">
            <div className="w-3 h-3 rounded bg-red-500/90" />
            <span className="text-muted-foreground">Strong Selling</span>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-3">
        {data.map((sector) => (
          <button
            key={sector.sector}
            onClick={() => onSectorClick(sector.sector)}
            className={`
              p-4 rounded-lg border-2 transition-all duration-200 text-left
              ${getHeatColor(sector.strongMoneyIntensity)}
              ${getBorderStyle(sector.sentiment)}
              hover:scale-[1.02] hover:shadow-lg
            `}
          >
            <div className="font-semibold text-sm truncate mb-2">{sector.sector}</div>
            <div className="space-y-1">
              <div className="flex justify-between items-center text-xs opacity-90">
                <span>R-Factor</span>
                <span className="font-mono font-bold">{sector.avgRFactor}</span>
              </div>
              <div className="flex justify-between items-center text-xs opacity-90">
                <span>Intensity</span>
                <span className="font-mono font-bold">
                  {sector.strongMoneyIntensity > 0 ? '+' : ''}
                  {sector.strongMoneyIntensity.toFixed(0)}%
                </span>
              </div>
              <div className="flex gap-2 mt-2 text-[10px]">
                {sector.buyingStocks > 0 && (
                  <span className="flex items-center gap-0.5">
                    <TrendingUp className="h-3 w-3" />
                    {sector.buyingStocks}
                  </span>
                )}
                {sector.sellingStocks > 0 && (
                  <span className="flex items-center gap-0.5">
                    <TrendingDown className="h-3 w-3" />
                    {sector.sellingStocks}
                  </span>
                )}
              </div>
            </div>
          </button>
        ))}
      </div>
    </div>
  );
}

// ============================================================================
// STOCK CARD COMPONENT
// ============================================================================

interface StockCardProps {
  stock: StockAnalysis;
  currencySymbol: string;
}

function StockCard({ stock, currencySymbol }: Readonly<StockCardProps>) {
  const isBullishToday = stock.intradayTrend === 'Bullish';

  // R-Factor indicator class for progress
  const getProgressIndicatorClass = (rFactor: number): string => {
    if (rFactor >= 80) return '[&>div]:bg-green-500';
    if (rFactor >= 50) return '[&>div]:bg-yellow-500';
    return '[&>div]:bg-red-500';
  };

  // R-Factor text color
  const getRFactorTextColor = (rFactor: number): string => {
    if (rFactor >= 80) return 'text-green-500';
    if (rFactor >= 50) return 'text-yellow-500';
    return 'text-red-500';
  };

  const href = `/stock/${encodeURIComponent(stock.symbol)}`;
  const tradeHref = `/simulator/${encodeURIComponent(stock.symbol)}?exchange=${encodeURIComponent(stock.exchange || 'US')}`;

  return (
    <div className={`p-3 rounded-lg border transition-all relative group ${
      isBullishToday 
        ? 'bg-background/50 hover:bg-accent/30 border-border/50' 
        : 'bg-red-500/5 hover:bg-red-500/10 border-red-500/20'
    }`}>
      {/* Trade Button - Absolute positioned */}
      <Link
        href={tradeHref}
        onClick={(e) => e.stopPropagation()}
        className="absolute top-2 right-2 z-10 opacity-0 group-hover:opacity-100 transition-opacity bg-yellow-500 hover:bg-yellow-600 text-black px-2 py-1 rounded text-[10px] font-semibold flex items-center gap-1"
        title={`Trade ${stock.symbol}`}
      >
        <Zap className="h-3 w-3" />
        Trade
      </Link>
      
      <Link
        href={href}
        className="block focus:outline-none focus-visible:ring-2 focus-visible:ring-yellow-500/50 rounded-lg"
        title={`View ${stock.symbol}`}
      >
      {/* Header: Symbol + Intraday Trend Badge */}
      <div className="flex justify-between items-start mb-2">
        <div>
          <span className="font-bold text-sm">{stock.symbol}</span>
          <p className="text-xs text-muted-foreground truncate max-w-[120px]">{stock.name}</p>
        </div>
        
        {/* Traffic Light Badge */}
        <Badge
          variant="outline"
          className={`text-[10px] px-1.5 flex items-center gap-1 ${
            isBullishToday
              ? 'border-green-500/50 text-green-500 bg-green-500/10'
              : 'border-red-500/50 text-red-500 bg-red-500/10'
          }`}
        >
          {isBullishToday ? (
            <>
              <CheckCircle2 className="h-3 w-3" />
              BULLISH
            </>
          ) : (
            <>
              <AlertTriangle className="h-3 w-3" />
              WAIT
            </>
          )}
        </Badge>
      </div>

      {/* R-Factor Strength Bar */}
      <div className="mb-2">
        <div className="flex justify-between items-center mb-1">
          <span className="text-xs text-muted-foreground">R-Factor</span>
          <span className={`text-xs font-bold font-mono ${getRFactorTextColor(stock.rFactor)}`}>
            {stock.rFactor}
          </span>
        </div>
        <Progress 
          value={stock.rFactor} 
          className={`h-1.5 bg-muted/30 ${getProgressIndicatorClass(stock.rFactor)}`}
        />
      </div>

      {/* Reasons Tags */}
      <div className="flex flex-wrap gap-1 mb-2">
        {stock.reasons.filter(r => r !== 'Rising Today' && r !== 'Profit Booking').map((reason) => (
          <span
            key={`${stock.symbol}-${reason}`}
            className="inline-block bg-yellow-500/10 border border-yellow-500/20 px-1.5 py-0.5 rounded text-[10px] text-yellow-600 dark:text-yellow-400"
          >
            {reason}
          </span>
        ))}
      </div>

      {/* Price & Change */}
      <div className="flex justify-between items-end pt-2 border-t border-border/30">
        <div className="text-xs text-muted-foreground">
          Open: <span className="font-mono">{currencySymbol}{stock.openPrice.toFixed(2)}</span>
        </div>
        <div className="text-right">
          <div className={`text-sm font-semibold ${stock.changePercent >= 0 ? 'text-green-500' : 'text-red-500'}`}>
            {currencySymbol}{stock.price.toFixed(2)}
          </div>
          <div className={`text-xs font-mono ${stock.changePercent >= 0 ? 'text-green-500' : 'text-red-500'}`}>
            {stock.changePercent >= 0 ? '+' : ''}
            {stock.changePercent.toFixed(2)}%
          </div>
        </div>
      </div>
      </Link>
    </div>
  );
}

// ============================================================================
// SECTOR DETAIL COMPONENT
// ============================================================================

interface SectorDetailProps {
  scope: SectorScope;
  id: string;
  currencySymbol: string;
}

const getIntensityStyle = (intensity: number): string => {
  if (intensity > 0) return 'bg-green-500/20 text-green-500';
  if (intensity < 0) return 'bg-red-500/20 text-red-500';
  return 'bg-muted text-muted-foreground';
};

function SectorDetail({ scope, id, currencySymbol }: Readonly<SectorDetailProps>) {
  return (
    <Card id={id} className="border-border/50 bg-card/40 backdrop-blur-sm scroll-mt-4">
      <CardHeader className="pb-3">
        <div className="flex justify-between items-start">
          <div>
            <CardTitle className="text-lg font-semibold">{scope.sector}</CardTitle>
            <p className="text-xs text-muted-foreground mt-1">
              Top {scope.stocks.length} by R-Factor • Avg R: {scope.heatmapData.avgRFactor}
            </p>
          </div>
          <div className="flex items-center gap-2">
            <Badge
              variant={scope.sentiment === 'Bullish' ? 'default' : 'destructive'}
              className="uppercase text-[10px] tracking-wider"
            >
              {scope.sentiment}
            </Badge>
            <div className={`text-xs font-mono font-bold px-2 py-1 rounded ${getIntensityStyle(scope.heatmapData.strongMoneyIntensity)}`}>
              {scope.heatmapData.strongMoneyIntensity > 0 ? '+' : ''}
              {scope.heatmapData.strongMoneyIntensity.toFixed(0)}%
            </div>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
          {scope.stocks.map((stock) => (
            <StockCard key={stock.symbol} stock={stock} currencySymbol={currencySymbol} />
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

// ============================================================================
// MAIN COMPONENT
// ============================================================================

export default function MarketScopePanel(props?: {
  market?: MarketType;
  showMarketTabs?: boolean;
}) {
  const showMarketTabs = props?.showMarketTabs ?? true;
  const [internalMarket, setInternalMarket] = useState<MarketType>(props?.market ?? 'US');

  useEffect(() => {
    if (props?.market) setInternalMarket(props.market);
  }, [props?.market]);

  const market = useMemo<MarketType>(() => props?.market ?? internalMarket, [internalMarket, props?.market]);
  const [data, setData] = useState<MarketScopeResult | null>(null);
  const [streamItems, setStreamItems] = useState<Array<{ symbol: string; exchange?: string }>>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

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

  const computeStreamItems = useCallback((result: MarketScopeResult, selectedMarket: MarketType) => {
    const exchange = selectedMarket === 'IN' ? 'BSE' : 'NASDAQ';
    const seen = new Set<string>();
    const items: Array<{ symbol: string; exchange?: string }> = [];

    for (const sector of result.sectors) {
      for (const s of sector.stocks) {
        const sym = canonicalSymbol(s.symbol);
        if (!sym) continue;
        const key = `${sym}::${exchange}`;
        if (seen.has(key)) continue;
        seen.add(key);
        items.push({ symbol: sym, exchange });
      }
    }

    return items;
  }, [canonicalSymbol]);

  const fetchData = useCallback(async (selectedMarket: MarketType) => {
    setLoading(true);
    setError(null);
    try {
      const result = await getStrongMoneyScope(selectedMarket);
      setData(result);
      setStreamItems(computeStreamItems(result, selectedMarket));
    } catch (err) {
      console.error('Failed to fetch market scope', err);
      setError('Failed to load market data. Please try again.');
    } finally {
      setLoading(false);
    }
  }, [computeStreamItems]);

  useEffect(() => {
    fetchData(market);
  }, [market, fetchData]);

  const applyStreamQuotes = useCallback((quotes: Array<Record<string, unknown>>) => {
    const updates = buildQuoteUpdateMap(quotes, canonicalSymbol);
    if (updates.size === 0) return;

    setData((prev) => {
      if (!prev) return prev;
      return applyQuoteUpdates({ prev, updates, canonicalSymbol });
    });
  }, [canonicalSymbol]);

  // Real-time price updates via SSE (same stream used by Watchlist).
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
      // Quiet reconnection (no full-page loading).
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
          const quotes = Array.isArray(payload?.quotes) ? (payload.quotes as Array<Record<string, unknown>>) : [];
          applyStreamQuotes(quotes);
        } catch (e) {
          console.error('Failed to parse quote stream payload', e);
        }
      });

      es.addEventListener('error', (evt) => {
        try {
          const payload = JSON.parse((evt as MessageEvent<string>).data) as { message?: string };
          if (payload?.message) console.error('Quote stream error:', payload.message);
        } catch {
          // ignore
        }
      });

      es.onerror = retry;
    }

    // Start all chunk streams.
    chunks.forEach((items) => startChunkStream(items));

    return () => {
      cancelled = true;
      sources.forEach((s) => s.close());
    };
  }, [applyStreamQuotes, error, fetchData, loading, market, streamItems]);

  const handleMarketChange = (value: string) => {
    setInternalMarket(value as MarketType);
  };

  const handleSectorClick = (sector: string) => {
    const element = document.getElementById(`sector-${sector.replaceAll(/\s+/g, '-').toLowerCase()}`);
    if (element) {
      element.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  };

  const currencySymbol = market === 'IN' ? '₹' : '$';

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-4">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold flex items-center gap-2">
              <Activity className="h-6 w-6 text-yellow-500" />
              Market Scope: Strong Money Flow
            </h1>
            <p className="text-muted-foreground text-sm mt-1">
              Track where institutional and insider money is flowing across sectors
            </p>
          </div>

          {/* Market Selector Tabs */}
          {showMarketTabs ? (
            <Tabs value={market} onValueChange={handleMarketChange} className="w-full sm:w-auto">
              <TabsList className="grid w-full grid-cols-2 sm:w-[280px] bg-muted/30">
                <TabsTrigger value="US" className="flex items-center gap-2 data-[state=active]:bg-yellow-500/20 data-[state=active]:text-yellow-500">
                  <Globe className="h-4 w-4" />
                  American
                </TabsTrigger>
                <TabsTrigger value="IN" className="flex items-center gap-2 data-[state=active]:bg-yellow-500/20 data-[state=active]:text-yellow-500">
                  <Building2 className="h-4 w-4" />
                  Indian
                </TabsTrigger>
              </TabsList>
            </Tabs>
          ) : null}
        </div>

        {/* Strategy Guide Button */}
        <div className="flex justify-end">
          <StrategyGuide />
        </div>
      </div>

      {/* Loading State */}
      {loading && (
        <div className="flex h-[50vh] w-full items-center justify-center">
          <div className="flex flex-col items-center gap-3">
            <TradingLoader />
            <p className="text-muted-foreground text-sm">
              Analyzing {market === 'IN' ? 'Indian' : 'American'} markets...
            </p>
          </div>
        </div>
      )}

      {/* Error State */}
      {error && !loading && (
        <div className="flex h-[30vh] w-full items-center justify-center">
          <div className="text-center">
            <p className="text-red-500 mb-2">{error}</p>
            <button
              onClick={() => fetchData(market)}
              className="text-primary hover:underline text-sm"
            >
              Try again
            </button>
          </div>
        </div>
      )}

      {/* Data Display */}
      {!loading && !error && data && (
        <>
          {/* Stats Bar with A/D Ratio */}
          <div className="flex flex-wrap gap-4 p-4 rounded-lg bg-yellow-500/5 border border-yellow-500/20">
            <div className="text-sm">
              <span className="text-muted-foreground">Stocks:</span>{' '}
              <span className="font-semibold text-yellow-500">{data.totalStocksAnalyzed}</span>
              <span className="text-muted-foreground"> total</span>
              <span className="text-muted-foreground"> • </span>
              <span className="font-semibold text-yellow-500">{data.totalStocksWithData}</span>
              <span className="text-muted-foreground"> live</span>
            </div>
            <div className="text-sm">
              <span className="text-muted-foreground">Active Sectors:</span>{' '}
              <span className="font-semibold text-yellow-500">{data.sectors.length}</span>
            </div>
            {/* A/D Ratio Display */}
            <div className="text-sm flex items-center gap-2">
              <span className="text-muted-foreground">A/D Ratio:</span>{' '}
              <Badge 
                variant="outline" 
                className={`font-mono font-bold ${getADRatioStyle(data.marketSentiment)}`}
              >
                {data.marketADRatio >= 999 ? '∞' : data.marketADRatio.toFixed(2)}
              </Badge>
              <span className="text-xs text-muted-foreground">
                ({data.marketAdvancing}↑ / {data.marketDeclining}↓)
              </span>
              <Badge 
                variant={getSentimentBadgeVariant(data.marketSentiment)}
                className="text-[10px]"
              >
                {data.marketSentiment}
              </Badge>
            </div>
            <div className="text-sm">
              <span className="text-muted-foreground">Last Updated:</span>{' '}
              <span className="font-semibold">{new Date(data.timestamp).toLocaleTimeString()}</span>
            </div>
          </div>

          {/* Summary / Empty / Warning */}
          {data.totalStocksWithData === 0 ? (
            <div className="flex items-start gap-3 p-4 rounded-lg bg-red-500/5 border border-red-500/20">
              <AlertTriangle className="h-5 w-5 text-red-500 mt-0.5" />
              <div className="text-sm">
                <p className="font-medium text-red-500">Live fundamentals/sector data is unavailable right now.</p>
                <p className="text-muted-foreground mt-1">
                  This usually happens when the upstream data provider blocks requests or rate-limits them. You can still
                  see the symbol list below, and prices may update as the live quote stream reconnects.
                </p>
              </div>
            </div>
          ) : null}

          {data.heatmap.length === 0 && data.totalStocksWithData > 0 ? (
            <div className="text-center text-muted-foreground py-6">
              No significant &ldquo;Strong Money&rdquo; activity detected in the {market === 'US' ? 'American' : 'Indian'} market today.
            </div>
          ) : null}

          {/* Heatmap Section (only if available) */}
          {data.heatmap.length > 0 ? (
            <SectorHeatmap data={data.heatmap} onSectorClick={handleSectorClick} />
          ) : null}

          {/* Detailed Sector Breakdown (always render if we have any sectors) */}
          <div className="space-y-4">
            <h3 className="text-lg font-semibold flex items-center gap-2">
              <TrendingUp className="h-5 w-5 text-yellow-500" />
              Detailed Sector Analysis
              <span className="text-xs text-muted-foreground font-normal ml-2">
                (Bullish Today first, then by R-Factor)
              </span>
            </h3>

            {data.sectors.length === 0 ? (
              <p className="text-muted-foreground text-center py-6">
                No sectors/stocks to display.
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
    </div>
  );
}
