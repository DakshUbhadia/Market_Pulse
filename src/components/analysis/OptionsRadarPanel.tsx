'use client';

import { useCallback, useEffect, useState, useRef } from 'react';
import { Zap, Flame, Bell } from 'lucide-react';
import { toast } from 'sonner';
import TradingLoader from '@/components/ui/TradingLoader';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { getMomentumRadar, type MomentumRadarItem } from '@/lib/actions/momentum.actions';
import { F_O_STOCKS } from '@/lib/constants';

type SortField = 'change15Min' | 'rsi' | 'volumeMultiple' | 'breakoutTime';

type RadarCachePayload = {
  timestamp: number;
  items: MomentumRadarItem[];
};

const normalizeFoSymbol = (symbol: string): string => {
  return String(symbol ?? '').trim().toUpperCase().replace(/\.(BO|NS)$/i, '');
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

const getRadarRefreshIntervalMs = () => {
  if (!isIndiaWeekday()) return 20 * 60 * 1000;

  const minuteOfDay = getIndiaMinuteOfDay();
  const preSessionStart = 9 * 60;
  const marketOpen = 9 * 60 + 15;
  const earlySessionEnd = 9 * 60 + 45;
  const marketClose = 15 * 60 + 30;

  if (minuteOfDay >= preSessionStart && minuteOfDay < marketOpen) return 45 * 1000;
  if (minuteOfDay >= marketOpen && minuteOfDay < earlySessionEnd) return 30 * 1000;
  if (minuteOfDay >= earlySessionEnd && minuteOfDay <= marketClose) return 2 * 60 * 1000;
  return 10 * 60 * 1000;
};

const getRadarCacheTtlMs = () => {
  if (!isIndiaWeekday()) return 4 * 60 * 60 * 1000;

  const minuteOfDay = getIndiaMinuteOfDay();
  const preSessionStart = 9 * 60;
  const earlySessionEnd = 9 * 60 + 45;
  const marketClose = 15 * 60 + 30;

  if (minuteOfDay >= preSessionStart && minuteOfDay < earlySessionEnd) return 60 * 1000;
  if (minuteOfDay >= earlySessionEnd && minuteOfDay <= marketClose) return 3 * 60 * 1000;
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

const parseRadarCachePayload = (raw: string): RadarCachePayload => {
  const parsed = JSON.parse(raw) as MomentumRadarItem[] | RadarCachePayload;
  if (Array.isArray(parsed)) {
    return { timestamp: 0, items: parsed };
  }

  return {
    timestamp: typeof parsed?.timestamp === 'number' ? parsed.timestamp : 0,
    items: Array.isArray(parsed?.items) ? parsed.items : [],
  };
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

  const points = data
    .map((value, i) => {
      const x = padding + (i / (data.length - 1)) * (width - 2 * padding);
      const y = height - padding - ((value - min) / range) * (height - 2 * padding);
      return `${x},${y}`;
    })
    .join(' ');

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

  return <Flame className="h-4 w-4 text-orange-500 animate-pulse" aria-label="High Volume" />;
};

/**
 * OptionsRadarPanel Component
 *
 * Specialized variant of MomentumRadarPanel that displays momentum analysis
 * exclusively for F&O (Futures & Options) eligible stocks from the F_O_stocks array.
 *
 * This component:
 * - Filters momentum radar results to only include F&O stocks
 * - Displays the same real-time momentum detection, RSI, and volume analysis
 * - Provides breakout notifications for F&O securities only
 * - Maintains all the original MomentumRadarPanel functionality
 */
export default function OptionsRadarPanel() {
  const [sortField, setSortField] = useState<SortField>('change15Min');
  const [items, setItems] = useState<MomentumRadarItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Track notified breakouts to avoid duplicate toasts
  const notifiedBreakoutsRef = useRef<Set<string>>(new Set());

  const getCacheKeyForDate = useCallback((dateKey: string) => `mp.optionsRadar.IN.${dateKey}`, []);

  const getTodayCacheKey = useCallback(() => {
    const today = new Date().toISOString().slice(0, 10);
    return getCacheKeyForDate(today);
  }, [getCacheKeyForDate]);

  const readFreshCache = useCallback((): boolean => {
    try {
      const cachedRaw = localStorage.getItem(getTodayCacheKey());
      if (!cachedRaw) return false;

      const payload = parseRadarCachePayload(cachedRaw);

      if (payload.items.length === 0) return false;
      if (payload.timestamp > 0 && Date.now() - payload.timestamp > getRadarCacheTtlMs()) return false;

      setItems(payload.items);
      setLoading(false);
      return true;
    } catch {
      return false;
    }
  }, [getTodayCacheKey]);

  const readRecentCacheFallback = useCallback((): boolean => {
    try {
      const dateKeys = getRecentDateKeys(7);
      const today = new Date().toISOString().slice(0, 10);

      for (const dateKey of dateKeys) {
        if (dateKey === today) continue;

        const raw = localStorage.getItem(getCacheKeyForDate(dateKey));
        if (!raw) continue;

        const payload = parseRadarCachePayload(raw);

        if (payload.items.length === 0) continue;

        setItems(payload.items);
        setLoading(false);
        return true;
      }
    } catch {
      return false;
    }

    return false;
  }, [getCacheKeyForDate]);

  const fetchRadar = useCallback(async (args?: { silent?: boolean }) => {
    const silent = Boolean(args?.silent);
    if (!silent) setLoading(true);
    setError(null);
    
    // Get F&O symbols as a Set for O(1) lookups
    const foSymbols = new Set(F_O_STOCKS.map((s) => normalizeFoSymbol(s.symbol)));
    
    try {
      // Fetch momentum radar for Indian market
      const result = await getMomentumRadar({ market: 'IN', limit: 300 });
      const resultArray = Array.isArray(result) ? result : [];

      // Filter to only include F&O stocks
      const foFilteredArray = resultArray.filter((item) => foSymbols.has(normalizeFoSymbol(item.symbol)));

      // Check for high-confidence breakouts (95%+) that happened RECENTLY (within last 5 minutes)
      const now = Date.now();
      const RECENT_BREAKOUT_THRESHOLD_MS = 5 * 60 * 1000; // 5 minutes

      const highConfidenceBreakouts = foFilteredArray.filter((item) => {
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
      showNotifications(highConfidenceBreakouts);

      // Replace items completely
      setItems(foFilteredArray);

      // Cache the results
      if (foFilteredArray.length > 0) {
        try {
          const payload: RadarCachePayload = {
            timestamp: Date.now(),
            items: foFilteredArray,
          };
          localStorage.setItem(getTodayCacheKey(), JSON.stringify(payload));
        } catch {
          /* ignore */
        }
      }
    } catch (e) {
      console.error('Failed to load Options Momentum Radar', e);
      setError('Failed to load F&O momentum data. Will show cached data if available.');
    } finally {
      if (!silent) setLoading(false);
    }
  }, [getTodayCacheKey]);

  const showNotifications = (breakouts: MomentumRadarItem[]) => {
    breakouts.slice(0, 3).forEach((item, index) => {
      const isPositive = item.change15Min > 0;
      const direction = isPositive ? '📈 Bullish' : '📉 Bearish';
      const marketLabel = '🇮🇳';
      const exchange = 'BSE';
      const tradeUrl = `/simulator/${item.symbol}?exchange=${exchange}`;

      setTimeout(() => {
        // NOSONAR - S2004: Acceptable nesting in callback function
        toast.success(`${marketLabel} ${direction} F&O Breakout!`, {
          description: `${item.symbol} detected with ${item.confidenceScore}% confidence. ${isPositive ? '+' : ''}${item.change15Min.toFixed(2)}% in 15 mins.`,
          duration: 10000,
          icon: <Bell className="h-4 w-4 text-yellow-500" />,
          action: {
            label: 'View',
            onClick: () => {
              globalThis.location.href = tradeUrl;
            },
          },
        });
      }, index * 500); // Stagger notifications
    });
  };

  useEffect(() => {
    const hasFreshCache = readFreshCache();
    const canUseFallback = !isIndiaMarketOpenWindow();
    const hasFallbackCache = !hasFreshCache && canUseFallback ? readRecentCacheFallback() : false;
    const hasAnyCache = hasFreshCache || hasFallbackCache;
    fetchRadar({ silent: hasAnyCache });
  }, [fetchRadar, readFreshCache, readRecentCacheFallback]);

  useEffect(() => {
    let cancelled = false;
    let timer: ReturnType<typeof setTimeout> | undefined;

    const schedule = () => {
      if (cancelled) return;
      const nextMs = getRadarRefreshIntervalMs();
      timer = setTimeout(() => {
        if (cancelled) return;
        if (typeof document !== 'undefined' && document.visibilityState === 'hidden') {
          schedule();
          return;
        }

        fetchRadar({ silent: true }).finally(schedule);
      }, nextMs);
    };

    schedule();

    return () => {
      cancelled = true;
      if (timer) clearTimeout(timer);
    };
  }, [fetchRadar]);

  const sorted = [...items].sort((a, b) => {
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
        const aVol = Number.parseFloat(a.volumeMultiple.replace('×', '')) || 0;
        const bVol = Number.parseFloat(b.volumeMultiple.replace('×', '')) || 0;
        return bVol - aVol;
      }
      case 'breakoutTime':
        return b.breakoutTime - a.breakoutTime;
      default:
        return 0;
    }
  });

  if (loading) {
    return (
      <div className="flex items-center justify-center p-8">
        <TradingLoader />
      </div>
    );
  }

  if (error) {
    return (
      <Card className="bg-red-500/10 border-red-500/30">
        <CardContent className="pt-6">
          <p className="text-red-500 text-sm">{error}</p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="bg-background/50 border-yellow-500/20">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between mb-4">
          <CardTitle className="flex items-center gap-2 text-yellow-500">
            <Zap className="h-5 w-5" />
            F&O Momentum Radar — Derivatives Breakout Detection
          </CardTitle>
          <div className="flex gap-2 flex-wrap justify-end">
            <Badge variant="outline" className="border-cyan-500/30 text-cyan-400 bg-cyan-500/10">
              {sorted.length} Signals
            </Badge>
          </div>
        </div>

        {/* Sort Controls */}
        <div className="flex gap-2 flex-wrap">
          {(
            [
              { field: 'change15Min' as SortField, label: '15M Change' },
              { field: 'rsi' as SortField, label: 'RSI (14)' },
              { field: 'volumeMultiple' as SortField, label: 'Volume Hot' },
              { field: 'breakoutTime' as SortField, label: 'Recent' },
            ] as const
          ).map(({ field, label }) => (
            <Button
              key={field}
              size="sm"
              variant={sortField === field ? 'default' : 'outline'}
              onClick={() => setSortField(field)}
              className={sortField === field ? 'bg-yellow-500/20 border-yellow-500 text-yellow-400' : ''}
            >
              {label}
            </Button>
          ))}
        </div>
      </CardHeader>

      <CardContent>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-muted-foreground/20 text-muted-foreground text-xs uppercase tracking-wider">
                <th className="px-3 py-2 text-left font-semibold">Symbol</th>
                <th className="px-3 py-2 text-right font-semibold">Price</th>
                <th className="px-3 py-2 text-right font-semibold">15M %</th>
                <th className="px-3 py-2 text-right font-semibold">RSI</th>
                <th className="px-3 py-2 text-center font-semibold">Volume</th>
                <th className="px-3 py-2 text-right font-semibold">Confidence</th>
                <th className="px-3 py-2 text-right font-semibold">Price Action</th>
              </tr>
            </thead>
            <tbody>
              {sorted.map((item) => {
                const isPositive = item.change15Min >= 0;
                return (
                  <tr
                    key={item.symbol}
                    className="border-b border-muted-foreground/10 hover:bg-muted/30 transition-colors cursor-pointer"
                    onClick={() => {
                      globalThis.location.href = `/simulator/${item.symbol}?exchange=BSE`;
                    }}
                  >
                    <td className="px-3 py-3 font-mono font-bold text-cyan-400">{item.symbol}</td>
                    <td className="px-3 py-3 text-right font-mono">{formatPrice(item.currentPrice)}</td>
                    <td className={`px-3 py-3 text-right font-mono font-bold ${isPositive ? 'text-emerald-400' : 'text-red-400'}`}>
                      {isPositive ? '+' : ''}{item.change15Min.toFixed(2)}%
                    </td>
                    <td className="px-3 py-3 text-right font-mono text-muted-foreground">{formatRSI(item.rsi)}</td>
                    <td className="px-3 py-3 text-center flex items-center justify-center gap-1">
                      <span className="text-amber-400 font-semibold">{item.volumeMultiple}</span>
                      <VolumeFireIcon volumeMultiple={item.volumeMultiple} />
                    </td>
                    <td className={`px-3 py-3 text-right font-bold ${getConfidenceTextClass(item.confidenceScore)}`}>
                      {item.confidenceScore.toFixed(0)}%
                    </td>
                    <td className="px-3 py-3">
                      <div className="flex justify-end">
                        <Sparkline data={item.priceHistory || []} isPositive={isPositive} />
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>

        {sorted.length === 0 && (
          <div className="py-8 text-center text-muted-foreground">
            <p>No momentum signals detected in F&O basket at this time.</p>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
