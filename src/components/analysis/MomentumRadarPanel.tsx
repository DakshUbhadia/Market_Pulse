'use client';

import { useCallback, useEffect, useMemo, useState, useRef, type ReactNode } from 'react';
import { Zap, TrendingUp, TrendingDown, Flame, ArrowUpDown, Bell } from 'lucide-react';
import { toast } from 'sonner';
import TradingLoader from '@/components/ui/TradingLoader';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { getMomentumRadar, type MomentumRadarItem } from '@/lib/actions/momentum.actions';
import type { MarketType } from '@/lib/constants';

type SortField = 'change15Min' | 'rsi' | 'volumeMultiple' | 'breakoutTime';

/**
 * Format time based on market timezone
 * US market: Show in EST (America/New_York)
 * Indian market: Show in IST (Asia/Kolkata)
 */
const formatTime = (epochMs: number, market?: 'US' | 'IN'): string => {
  if (!Number.isFinite(epochMs) || epochMs <= 0) return '--:--';
  const d = new Date(epochMs);
  
  // Determine timezone based on market
  const timeZone = market === 'US' ? 'America/New_York' : 'Asia/Kolkata';
  const suffix = market === 'US' ? ' EST' : ' IST';
  
  try {
    const formatted = new Intl.DateTimeFormat('en-US', {
      hour: 'numeric',
      minute: '2-digit',
      hour12: true,
      timeZone,
    }).format(d);
    
    return formatted + suffix;
  } catch {
    // Fallback to local time if timezone fails
    return new Intl.DateTimeFormat(undefined, {
      hour: 'numeric',
      minute: '2-digit',
    }).format(d);
  }
};

const formatStrength = (value: number): string => {
  if (!Number.isFinite(value)) return '0.00%';
  const sign = value >= 0 ? '+' : '';
  return `${sign}${value.toFixed(2)}%`;
};

const formatRSI = (value: number): string => {
  if (!Number.isFinite(value)) return '--';
  return value.toFixed(1);
};

const formatPrice = (value: number): string => {
  if (!Number.isFinite(value)) return '--';
  return value.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
};

const getConfidenceTextClass = (confidence: number): string => {
  if (confidence >= 70) return 'text-emerald-400';
  if (confidence >= 50) return 'text-amber-400';
  return 'text-muted-foreground';
};

const getConfidenceBarClass = (confidence: number): string => {
  if (confidence >= 70) return 'bg-emerald-500';
  if (confidence >= 50) return 'bg-amber-500';
  return 'bg-muted';
};

/**
 * Mini sparkline component for price history
 */
const Sparkline = ({ data, isPositive }: { data: number[]; isPositive: boolean }) => {
  if (!data || data.length < 2) return null;
  
  const min = Math.min(...data);
  const max = Math.max(...data);
  const range = max - min || 1;
  
  const height = 24;
  const width = 60;
  const padding = 2;
  
  const points = data.map((value, i) => {
    const x = padding + (i / (data.length - 1)) * (width - 2 * padding);
    const y = height - padding - ((value - min) / range) * (height - 2 * padding);
    return `${x},${y}`;
  }).join(' ');
  
  const strokeColor = isPositive ? '#34d399' : '#f87171';
  
  return (
    <svg width={width} height={height} className="inline-block">
      <polyline
        fill="none"
        stroke={strokeColor}
        strokeWidth="1.5"
        points={points}
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
};

/**
 * Fire icon component for high RVOL stocks
 */
const VolumeFireIcon = ({ volumeMultiple }: { volumeMultiple: string }) => {
  const numericValue = Number.parseFloat(volumeMultiple.replace('×', ''));
  if (!Number.isFinite(numericValue) || numericValue < 3) return null;
  
  return (
    <Flame className="h-4 w-4 text-orange-500 animate-pulse" aria-label="High Volume" />
  );
};

export default function MomentumRadarPanel(props?: {
  market?: MarketType;
  showMarketTabs?: boolean;
}) {
  const showMarketTabs = props?.showMarketTabs ?? true;
  const [internalMarket, setInternalMarket] = useState<MarketType>(props?.market ?? 'IN');
  const [sortField, setSortField] = useState<SortField>('change15Min');

  useEffect(() => {
    if (props?.market) setInternalMarket(props.market);
  }, [props?.market]);

  const market: MarketType = props?.market ?? internalMarket;
  const [items, setItems] = useState<MomentumRadarItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  // Track notified breakouts to avoid duplicate toasts
  const notifiedBreakoutsRef = useRef<Set<string>>(new Set());

  // Cache key includes market and today's date
  const getCacheKey = (m: MarketType) => {
    const today = new Date().toISOString().slice(0, 10); // YYYY-MM-DD
    return `mp.momentumRadar.${m}.${today}`;
  };

  // Clear items and load cached data when market changes
  useEffect(() => {
    // Clear previous items when market changes to avoid mixing
    setItems([]);
    setLoading(true);
    
    try {
      const cached = localStorage.getItem(getCacheKey(market));
      if (cached) {
        const parsed = JSON.parse(cached) as MomentumRadarItem[];
        if (Array.isArray(parsed) && parsed.length > 0) {
          setItems(parsed);
          setLoading(false);
        }
      }
    } catch { /* ignore cache errors */ }
  }, [market]);

  const fetchRadar = useCallback(async (m: MarketType) => {
    setLoading(true);
    setError(null);
    try {
      // Fetch ALL detected momentum stocks throughout the day (no limit)
      const result = await getMomentumRadar({ market: m, limit: 100 });
      const resultArray = Array.isArray(result) ? result : [];
      
      // Check for high-confidence breakouts (95%+) that happened RECENTLY (within last 5 minutes)
      const now = Date.now();
      const RECENT_BREAKOUT_THRESHOLD_MS = 5 * 60 * 1000; // 5 minutes
      
      const highConfidenceBreakouts = resultArray.filter(item => {
        const key = `${item.symbol}-${item.breakoutTime}`;
        const breakoutAge = now - item.breakoutTime;
        
        // Only notify if:
        // 1. 95%+ confidence
        // 2. Breakout happened within last 5 minutes (recent)
        // 3. Not already notified
        if (
          item.confidenceScore >= 95 && 
          breakoutAge >= 0 && 
          breakoutAge <= RECENT_BREAKOUT_THRESHOLD_MS &&
          !notifiedBreakoutsRef.current.has(key)
        ) {
          notifiedBreakoutsRef.current.add(key);
          return true;
        }
        return false;
      });
      
      // Show toast for each high-confidence breakout (max 3 at a time to avoid spam)
      highConfidenceBreakouts.slice(0, 3).forEach((item, index) => {
        const isPositive = item.change15Min > 0;
        const direction = isPositive ? '📈 Bullish' : '📉 Bearish';
        const marketLabel = m === 'IN' ? '🇮🇳' : '🇺🇸';
        const exchange = m === 'IN' ? 'NSE' : 'NASDAQ';
        const tradeUrl = `/simulator/${item.symbol}?exchange=${exchange}`;
        
        setTimeout(() => {
          toast.success(`${marketLabel} ${direction} Breakout Alert!`, {
            description: `${item.symbol} detected with ${item.confidenceScore}% confidence. ${isPositive ? '+' : ''}${item.change15Min.toFixed(2)}% in 15 mins.`,
            duration: 10000,
            icon: <Bell className="h-4 w-4 text-yellow-500" />,
            action: {
              label: 'View',
              onClick: () => { globalThis.location.href = tradeUrl; },
            },
          });
        }, index * 500); // Stagger notifications
      });
      
      // Replace items completely (no merging to avoid mixing markets)
      setItems(resultArray);
      
      // Cache the results for this market
      if (resultArray.length > 0) {
        try {
          localStorage.setItem(getCacheKey(m), JSON.stringify(resultArray));
        } catch { /* ignore */ }
      }
    } catch (e) {
      console.error('Failed to load Momentum Radar', e);
      setError('Failed to load Momentum Radar. Will show cached data if available.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchRadar(market);
  }, [market, fetchRadar]);

  const sorted = useMemo(() => {
    return [...items].sort((a, b) => {
      // Primary sort: confidence (highest first)
      const confDiff = b.confidenceScore - a.confidenceScore;
      // Use a threshold of 5 points to group similar confidence levels
      if (Math.abs(confDiff) >= 5) return confDiff;
      
      // Secondary sort: within similar confidence, sort by selected field
      switch (sortField) {
        case 'change15Min':
          return b.change15Min - a.change15Min;
        case 'rsi':
          return b.rsi - a.rsi;
        case 'volumeMultiple': {
          const aVol = Number.parseFloat(a.volumeMultiple.replace('×', ''));
          const bVol = Number.parseFloat(b.volumeMultiple.replace('×', ''));
          return bVol - aVol;
        }
        case 'breakoutTime':
          // Latest breakout first (higher timestamp = more recent)
          return b.breakoutTime - a.breakoutTime;
        default:
          return b.change15Min - a.change15Min;
      }
    });
  }, [items, sortField]);

  const cycleSortField = () => {
    const fields: SortField[] = ['change15Min', 'rsi', 'volumeMultiple', 'breakoutTime'];
    const currentIndex = fields.indexOf(sortField);
    const nextIndex = (currentIndex + 1) % fields.length;
    setSortField(fields[nextIndex]);
  };

  const getSortLabel = () => {
    switch (sortField) {
      case 'change15Min':
        return '15m %';
      case 'rsi':
        return 'RSI';
      case 'volumeMultiple':
        return 'RVOL';
      case 'breakoutTime':
        return 'Latest';
      default:
        return '15m %';
    }
  };

  let content: ReactNode;
  if (loading && items.length === 0) {
    content = (
      <div className="flex flex-col items-center justify-center gap-3 py-8">
        <TradingLoader />
        <span className="text-muted-foreground text-sm">Scanning for momentum breakouts…</span>
      </div>
    );
  } else if (error && sorted.length === 0) {
    content = <div className="text-sm text-red-500">{error}</div>;
  } else if (sorted.length === 0) {
    content = (
      <div className="text-sm text-muted-foreground p-4 rounded-lg bg-muted/20 border border-muted">
        <p className="font-medium mb-2">No momentum breakouts detected right now.</p>
        <p className="text-xs">
          Momentum Radar detects price breakouts (price breaks above 20-period high or below 20-period low).
          Check back during market hours for live breakout alerts.
        </p>
      </div>
    );
  } else {
    // Already sorted by confidence (primary) and selected field (secondary) in useMemo

    content = (
      <div className="space-y-3">
        {/* Explanation of confidence */}
        <div className="text-xs text-cyan-400/80 bg-cyan-500/10 border border-cyan-500/20 rounded-lg px-3 py-2 flex items-start gap-2">
          <span className="text-cyan-400 mt-0.5">📊</span>
          <span>
            <strong>Confidence</strong> shows probability price continues in breakout direction.
            Based on <strong>institutional activity</strong>: continuous buying → bullish, continuous selling → bearish.
            Time shown is when momentum first changed today.
          </span>
        </div>

        <div className="max-h-[420px] overflow-y-auto pr-2 scrollbar-thin scrollbar-thumb-cyan-500/30 scrollbar-track-transparent">
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-3">
        {sorted.map((s) => {
          const isBull = s.signalType === 'Bullish Breakout';
          const isHighConf = s.confidenceScore >= 70;
          
          // For visual consistency: use ACTUAL price movement to determine colors
          // This ensures the card "looks" correct even if momentum is changing
          const actuallyGoingUp = s.change15Min > 0;
          const glow = isHighConf && Math.abs(s.change15Min) > 0.5;

          // Determine wrapper class based on glow and signal direction
          let wrapperClassName: string | undefined;
          if (glow && isBull) {
            wrapperClassName = 'rounded-xl p-px bg-linear-to-r from-emerald-500/40 via-emerald-500/20 to-cyan-500/20 shadow-[0_0_25px_rgba(16,185,129,0.25)]';
          } else if (glow && !isBull) {
            wrapperClassName = 'rounded-xl p-px bg-linear-to-r from-red-500/40 via-red-500/20 to-orange-500/20 shadow-[0_0_25px_rgba(239,68,68,0.25)]';
          }

          // Determine card class based on glow and direction
          let cardClassName = 'border-white/10';
          if (glow && isBull) {
            cardClassName = 'border-emerald-500/30';
          } else if (glow && !isBull) {
            cardClassName = 'border-red-500/30';
          }

          const badgeClassName = isBull
            ? 'bg-emerald-500/10 text-emerald-300 border border-emerald-500/20'
            : 'bg-red-500/10 text-red-300 border border-red-500/20';
          
          // Show actual price change color (regardless of signal type)
          const change15MinClassName = actuallyGoingUp
            ? 'text-xl font-bold text-emerald-300'
            : 'text-xl font-bold text-red-300';

          return (
            <div key={`${s.symbol}-${s.signalType}-${s.breakoutTime}`} className={wrapperClassName}>
              <Card className={cardClassName}>
                <CardContent className="p-3">
                  {/* Header: Symbol, Time, Badge */}
                  <div className="flex items-start justify-between gap-2">
                    <div>
                      <div className="flex items-center gap-1">
                        <span className="font-semibold leading-none">{s.symbol}</span>
                        <VolumeFireIcon volumeMultiple={s.volumeMultiple} />
                      </div>
                      <div className="text-xs text-muted-foreground mt-1 line-clamp-1">{s.sector}</div>
                    </div>
                    <div className="flex flex-col items-end gap-1">
                      <Badge variant="secondary" className={badgeClassName}>
                        <span className="inline-flex items-center gap-1">
                          {isBull ? <TrendingUp className="h-3 w-3" /> : <TrendingDown className="h-3 w-3" />}
                          {isBull ? 'Bullish' : 'Bearish'}
                        </span>
                      </Badge>
                      {/* Prominent breakout time - formatted for market timezone */}
                      <span className="text-[10px] text-cyan-400 font-medium">
                        ⏱️ {formatTime(s.breakoutTime, s.market)}
                      </span>
                    </div>
                  </div>

                  {/* Main metrics: Current Change and Sparkline */}
                  <div className="mt-3 flex items-center justify-between">
                    <div>
                      <div className="text-xs text-muted-foreground">Current Move</div>
                      <div className={change15MinClassName}>{formatStrength(s.change15Min)}</div>
                    </div>
                    {s.priceHistory && s.priceHistory.length > 1 && (
                      <Sparkline data={s.priceHistory} isPositive={s.change15Min >= 0} />
                    )}
                  </div>

                  {/* Secondary metrics row */}
                  <div className="mt-3 grid grid-cols-3 gap-2 text-xs">
                    <div>
                      <div className="text-muted-foreground">RSI(14)</div>
                      <div className={s.rsi >= 70 ? 'text-amber-400 font-medium' : 'text-foreground'}>
                        {formatRSI(s.rsi)}
                      </div>
                    </div>
                    <div>
                      <div className="text-muted-foreground">RVOL</div>
                      <div className={Number.parseFloat(s.volumeMultiple.replace('×', '')) >= 2 ? 'text-orange-400 font-medium' : 'text-foreground'}>
                        {s.volumeMultiple}
                      </div>
                    </div>
                    <div>
                      <div className="text-muted-foreground">Price</div>
                      <div className="text-foreground">{formatPrice(s.currentPrice)}</div>
                    </div>
                  </div>

                  {/* Confidence Score Bar */}
                  {'confidenceScore' in s && typeof s.confidenceScore === 'number' && (
                    <div className="mt-3">
                      <div className="flex items-center justify-between text-xs mb-1">
                        <span className="text-muted-foreground" title={isBull ? 'Probability price continues UP' : 'Probability price continues DOWN'}>
                          {isBull ? '↑ Likely to rise' : '↓ Likely to fall'}
                        </span>
                        <span className={`font-medium ${getConfidenceTextClass(s.confidenceScore)}`}>
                          {s.confidenceScore}%
                        </span>
                      </div>
                      <div className="h-1.5 bg-muted/30 rounded-full overflow-hidden">
                        <div 
                          className={`h-full rounded-full transition-all ${getConfidenceBarClass(s.confidenceScore)}`}
                          style={{ width: `${Math.min(100, Math.max(0, s.confidenceScore))}%` }}
                        />
                      </div>
                    </div>
                  )}

                  {/* Signal Reason - factors contributing to confidence */}
                  {'reason' in s && typeof s.reason === 'string' && s.reason && (
                    <div className="mt-2 text-[10px] text-muted-foreground bg-muted/20 rounded px-2 py-1 line-clamp-2" title="Factors affecting confidence">
                      {s.reason}
                    </div>
                  )}

                  {/* Footer: Price at breakout */}
                  <div className="mt-2 flex items-center justify-between text-xs text-muted-foreground">
                    <span>Breakout Price: {formatPrice(s.breakoutPrice)}</span>
                    <span>Now: {formatPrice(s.currentPrice)}</span>
                  </div>
                </CardContent>
              </Card>
            </div>
          );
        })}
        </div>
        </div>
      </div>
    );
  }

  return (
    <Card className="border-cyan-500/20 bg-background/60 backdrop-blur">
      <CardHeader className="flex flex-row items-center justify-between gap-4">
        <div className="flex items-center gap-2">
          <div className="relative">
            <Zap className="h-5 w-5 text-cyan-400 animate-pulse" />
            <span className="absolute -inset-1 rounded-full bg-cyan-500/10 blur-md" />
          </div>
          <CardTitle className="text-lg font-semibold">⚡ Momentum Radar</CardTitle>
          <Badge variant="secondary" className="bg-cyan-500/10 text-cyan-300 border border-cyan-500/20">
            Hybrid Breakout Engine
          </Badge>
          {/* Show signal count when we have results */}
          {items.length > 0 && (
            <Badge variant="outline" className="text-xs ml-2 text-muted-foreground">
              {items.length} {items.length === 1 ? 'signal' : 'signals'}
            </Badge>
          )}
        </div>

        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={cycleSortField}
            className="h-8 px-2 text-xs gap-1"
          >
            <ArrowUpDown className="h-3 w-3" />
            Sort: {getSortLabel()}
          </Button>

          {showMarketTabs ? (
            <Tabs value={market} onValueChange={(v) => setInternalMarket(v as MarketType)}>
              <TabsList className="bg-background/40 border border-white/10">
                <TabsTrigger value="US">US</TabsTrigger>
                <TabsTrigger value="IN">India</TabsTrigger>
              </TabsList>
            </Tabs>
          ) : null}
        </div>
      </CardHeader>

      <CardContent>
        {content}
      </CardContent>
    </Card>
  );
}
