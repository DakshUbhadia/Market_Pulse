'use client';

import { useEffect, useRef, useState, useCallback } from 'react';
import { createChart, type IChartApi, type ISeriesApi, type CandlestickSeriesOptions, type HistogramSeriesOptions, ColorType, CandlestickSeries, HistogramSeries, type Time } from 'lightweight-charts';
import { getHistoricalCandles } from '@/lib/actions/trading.actions';
import TradingLoader from '@/components/ui/TradingLoader';

type TimeRange = '1d' | '5d' | '1mo' | '3mo';
type ChartInterval = '1m' | '5m' | '15m' | '1h' | '1d';

interface RealtimeChartProps {
  readonly symbol: string;
  readonly exchange?: string;
  readonly className?: string;
  readonly height?: number;
  readonly showControls?: boolean;
  readonly onPriceUpdate?: (price: number) => void;
}

const RANGE_CONFIG: Record<TimeRange, { label: string; interval: ChartInterval }> = {
  '1d': { label: '1D', interval: '5m' },
  '5d': { label: '5D', interval: '15m' },
  '1mo': { label: '1M', interval: '1h' },
  '3mo': { label: '3M', interval: '1d' },
};

/**
 * Check if exchange is Indian (BSE/NSE)
 */
function isIndianExchange(exchange: string): boolean {
  const exch = (exchange || 'US').toUpperCase();
  return exch === 'BSE' || exch === 'NSE' || exch === 'BO' || exch === 'NS' || exch === 'IN';
}

/**
 * Get currency symbol based on exchange
 */
function getCurrencySymbol(exchange: string): string {
  return isIndianExchange(exchange) ? '₹' : '$';
}

/**
 * Format price with appropriate currency
 */
function formatPrice(price: number, exchange: string): string {
  const isIndian = isIndianExchange(exchange);
  if (isIndian) {
    return `₹${price.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  }
  return `$${price.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

/**
 * Get timezone for exchange
 */
function getExchangeTimezone(exchange: string): string {
  return isIndianExchange(exchange) ? 'Asia/Kolkata' : 'America/New_York';
}

/**
 * Get timezone abbreviation for display
 */
function getTimezoneAbbr(exchange: string): string {
  return isIndianExchange(exchange) ? 'IST' : 'EST';
}

/**
 * Check if the market is currently open
 * US Market: 9:30 AM - 4:00 PM EST (Mon-Fri)
 * Indian Market: 9:15 AM - 3:30 PM IST (Mon-Fri)
 */
function isMarketOpen(exchange: string): boolean {
  const now = new Date();
  const dayOfWeek = now.getDay();
  
  // Weekend check (0 = Sunday, 6 = Saturday)
  if (dayOfWeek === 0 || dayOfWeek === 6) {
    return false;
  }
  
  if (isIndianExchange(exchange)) {
    // Indian market: 9:15 AM - 3:30 PM IST
    const istFormatter = new Intl.DateTimeFormat('en-US', {
      timeZone: 'Asia/Kolkata',
      hour: 'numeric',
      minute: 'numeric',
      hour12: false,
    });
    const parts = istFormatter.formatToParts(now);
    const hour = Number.parseInt(parts.find(p => p.type === 'hour')?.value ?? '0', 10);
    const minute = Number.parseInt(parts.find(p => p.type === 'minute')?.value ?? '0', 10);
    const timeInMinutes = hour * 60 + minute;
    
    // 9:15 AM = 555 minutes, 3:30 PM = 930 minutes
    return timeInMinutes >= 555 && timeInMinutes < 930;
  } else {
    // US market: 9:30 AM - 4:00 PM EST
    const estFormatter = new Intl.DateTimeFormat('en-US', {
      timeZone: 'America/New_York',
      hour: 'numeric',
      minute: 'numeric',
      hour12: false,
    });
    const parts = estFormatter.formatToParts(now);
    const hour = Number.parseInt(parts.find(p => p.type === 'hour')?.value ?? '0', 10);
    const minute = Number.parseInt(parts.find(p => p.type === 'minute')?.value ?? '0', 10);
    const timeInMinutes = hour * 60 + minute;
    
    // 9:30 AM = 570 minutes, 4:00 PM = 960 minutes
    return timeInMinutes >= 570 && timeInMinutes < 960;
  }
}

/**
 * Calculate appropriate price scale margins based on price range
 * This ensures candles look natural regardless of the stock's price volatility
 */
function calculatePriceScaleMargins(candles: Array<{ high: number; low: number }>): { top: number; bottom: number } {
  if (candles.length === 0) return { top: 0.1, bottom: 0.2 };
  
  const highs = candles.map(c => c.high);
  const lows = candles.map(c => c.low);
  const maxPrice = Math.max(...highs);
  const minPrice = Math.min(...lows);
  const priceRange = maxPrice - minPrice;
  const avgPrice = (maxPrice + minPrice) / 2;
  
  // Calculate volatility as percentage of average price
  const volatilityPercent = avgPrice > 0 ? (priceRange / avgPrice) * 100 : 0;
  
  // Adjust margins based on volatility
  // Higher volatility = smaller margins to show more price action
  // Lower volatility = larger margins to prevent flat-looking charts
  if (volatilityPercent > 10) {
    // High volatility - use tight margins
    return { top: 0.05, bottom: 0.15 };
  } else if (volatilityPercent > 5) {
    // Medium volatility
    return { top: 0.08, bottom: 0.18 };
  } else if (volatilityPercent > 2) {
    // Low volatility
    return { top: 0.1, bottom: 0.2 };
  } else {
    // Very low volatility - expand margins to show subtle movements
    return { top: 0.15, bottom: 0.25 };
  }
}

export default function RealtimeChart({
  symbol,
  exchange = 'US',
  className = '',
  height = 400,
  showControls = true,
  onPriceUpdate,
}: RealtimeChartProps) {
  const chartContainerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const candleSeriesRef = useRef<ISeriesApi<'Candlestick'> | null>(null);
  const volumeSeriesRef = useRef<ISeriesApi<'Histogram'> | null>(null);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [range, setRange] = useState<TimeRange>('1d');
  const [lastPrice, setLastPrice] = useState<number | null>(null);
  const [marketOpen, setMarketOpen] = useState(() => isMarketOpen(exchange));
  
  // Track last candle for proper updates
  const lastCandleRef = useRef<{ time: number; open: number; high: number; low: number; close: number } | null>(null);
  const intervalMs = useRef<number>(300000); // Default 5 min
  
  // Use ref for callback to avoid re-renders
  const onPriceUpdateRef = useRef(onPriceUpdate);
  onPriceUpdateRef.current = onPriceUpdate;

  // Store exchange ref for use in chart callbacks
  const exchangeRef = useRef(exchange);
  exchangeRef.current = exchange;
  
  // Check market status periodically
  useEffect(() => {
    const checkMarketStatus = () => {
      setMarketOpen(isMarketOpen(exchange));
    };
    
    // Check every minute
    const intervalId = setInterval(checkMarketStatus, 60000);
    
    return () => clearInterval(intervalId);
  }, [exchange]);

  // Initialize chart
  useEffect(() => {
    if (!chartContainerRef.current) return;

    const chart = createChart(chartContainerRef.current, {
      width: chartContainerRef.current.clientWidth,
      height,
      layout: {
        background: { type: ColorType.Solid, color: 'transparent' },
        textColor: '#9ca3af',
      },
      grid: {
        vertLines: { color: 'rgba(255, 255, 255, 0.05)' },
        horzLines: { color: 'rgba(255, 255, 255, 0.05)' },
      },
      crosshair: {
        mode: 1,
        vertLine: {
          width: 1,
          color: 'rgba(234, 179, 8, 0.5)',
          style: 2,
        },
        horzLine: {
          width: 1,
          color: 'rgba(234, 179, 8, 0.5)',
          style: 2,
        },
      },
      rightPriceScale: {
        borderColor: 'rgba(255, 255, 255, 0.1)',
        scaleMargins: {
          top: 0.1,
          bottom: 0.2,
        },
        autoScale: true,
        alignLabels: true,
      },
      timeScale: {
        borderColor: 'rgba(255, 255, 255, 0.1)',
        timeVisible: true,
        secondsVisible: false,
        rightOffset: 5,
        barSpacing: 8,
        minBarSpacing: 4,
        fixLeftEdge: true,
        fixRightEdge: true,
        tickMarkFormatter: (time: number) => {
          const date = new Date(time * 1000);
          const currentExchange = exchangeRef.current;
          const tz = getExchangeTimezone(currentExchange);
          const tzAbbr = getTimezoneAbbr(currentExchange);
          
          const formatter = new Intl.DateTimeFormat('en-US', {
            timeZone: tz,
            hour: '2-digit',
            minute: '2-digit',
            hour12: false,
          });
          
          return `${formatter.format(date)} ${tzAbbr}`;
        },
      },
      localization: {
        priceFormatter: (price: number) => {
          const currencySymbol = getCurrencySymbol(exchangeRef.current);
          if (isIndianExchange(exchangeRef.current)) {
            return `${currencySymbol}${price.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
          }
          return `${currencySymbol}${price.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
        },
        timeFormatter: (time: number) => {
          const date = new Date(time * 1000);
          const currentExchange = exchangeRef.current;
          const tz = getExchangeTimezone(currentExchange);
          const tzAbbr = getTimezoneAbbr(currentExchange);
          
          const formatter = new Intl.DateTimeFormat('en-US', {
            timeZone: tz,
            month: 'short',
            day: '2-digit',
            hour: '2-digit',
            minute: '2-digit',
            hour12: false,
          });
          
          return `${formatter.format(date)} ${tzAbbr}`;
        },
      },
      handleScroll: {
        mouseWheel: true,
        pressedMouseMove: true,
        horzTouchDrag: true,
        vertTouchDrag: false,
      },
      handleScale: {
        axisPressedMouseMove: true,
        mouseWheel: true,
        pinch: true,
      },
    });

    // Add candlestick series using v5 API
    const candleSeries = chart.addSeries(CandlestickSeries, {
      upColor: '#22c55e',
      downColor: '#ef4444',
      borderUpColor: '#22c55e',
      borderDownColor: '#ef4444',
      wickUpColor: '#22c55e',
      wickDownColor: '#ef4444',
    } as CandlestickSeriesOptions);

    // Add volume series using v5 API
    const volumeSeries = chart.addSeries(HistogramSeries, {
      color: '#3b82f6',
      priceFormat: {
        type: 'volume',
      },
      priceScaleId: '',
    } as HistogramSeriesOptions);

    volumeSeries.priceScale().applyOptions({
      scaleMargins: {
        top: 0.85,
        bottom: 0,
      },
    });

    chartRef.current = chart;
    candleSeriesRef.current = candleSeries;
    volumeSeriesRef.current = volumeSeries;

    // Handle resize with ResizeObserver for better responsiveness
    const resizeObserver = new ResizeObserver((entries) => {
      for (const entry of entries) {
        if (chartRef.current && entry.contentRect.width > 0) {
          chartRef.current.applyOptions({
            width: entry.contentRect.width,
            height: entry.contentRect.height || height,
          });
          // Refit content after resize
          chartRef.current.timeScale().fitContent();
        }
      }
    });

    if (chartContainerRef.current) {
      resizeObserver.observe(chartContainerRef.current);
    }

    // Also listen to window resize as fallback
    const handleResize = () => {
      if (chartContainerRef.current && chartRef.current) {
        chartRef.current.applyOptions({
          width: chartContainerRef.current.clientWidth,
        });
      }
    };

    window.addEventListener('resize', handleResize);

    return () => {
      window.removeEventListener('resize', handleResize);
      resizeObserver.disconnect();
      chart.remove();
      chartRef.current = null;
      candleSeriesRef.current = null;
      volumeSeriesRef.current = null;
    };
  }, [height, exchange]);

  // Fetch and update data
  const fetchData = useCallback(async () => {
    if (!candleSeriesRef.current || !volumeSeriesRef.current || !chartRef.current) return;

    setLoading(true);
    setError(null);

    try {
      const config = RANGE_CONFIG[range];
      const result = await getHistoricalCandles(symbol, config.interval, range, exchange);

      if (result.error) {
        setError(result.error);
        return;
      }

      if (result.candles.length === 0) {
        setError('No data available');
        return;
      }

      // Convert to chart format
      const candleData = result.candles.map((c) => ({
        time: c.time as Time,
        open: c.open,
        high: c.high,
        low: c.low,
        close: c.close,
      }));

      const volumeData = result.candles.map((c) => ({
        time: c.time as Time,
        value: c.volume,
        color: c.close >= c.open ? 'rgba(34, 197, 94, 0.5)' : 'rgba(239, 68, 68, 0.5)',
      }));

      // Calculate dynamic price scale margins based on data volatility
      const priceMargins = calculatePriceScaleMargins(result.candles);
      
      // Apply dynamic margins to price scale for natural-looking candles
      chartRef.current.priceScale('right').applyOptions({
        scaleMargins: priceMargins,
        autoScale: true,
      });

      candleSeriesRef.current.setData(candleData);
      volumeSeriesRef.current.setData(volumeData);

      // Set last price and track last candle
      const lastCandle = result.candles.at(-1);
      if (lastCandle) {
        setLastPrice(lastCandle.close);
        onPriceUpdateRef.current?.(lastCandle.close);
        lastCandleRef.current = {
          time: lastCandle.time,
          open: lastCandle.open,
          high: lastCandle.high,
          low: lastCandle.low,
          close: lastCandle.close,
        };
      }
      
      // Set interval based on range config
      const intervalMap: Record<ChartInterval, number> = {
        '1m': 60000,
        '5m': 300000,
        '15m': 900000,
        '1h': 3600000,
        '1d': 86400000,
      };
      intervalMs.current = intervalMap[config.interval];

      // Fit content to show all data properly
      chartRef.current?.timeScale().fitContent();
      
      // Force chart to recalculate visible range
      setTimeout(() => {
        chartRef.current?.timeScale().scrollToRealTime();
      }, 100);
    } catch (err) {
      console.error('Chart data fetch error:', err);
      setError('Failed to load chart data');
    } finally {
      setLoading(false);
    }
  }, [symbol, exchange, range]);

  // Fetch data on mount and range change
  useEffect(() => {
    fetchData();
  }, [fetchData]);

  // SSE streaming for real-time updates - only when market is open
  useEffect(() => {
    if (!symbol || !marketOpen) return;

    let eventSource: EventSource | null = null;
    let reconnectTimeout: ReturnType<typeof setTimeout> | null = null;
    let retryCount = 0;
    const MAX_RETRIES = 5;

    const connect = () => {
      const items = [{ symbol, exchange }];
      const itemsParam = encodeURIComponent(JSON.stringify(items));
      const url = `/api/quotes/stream?items=${itemsParam}`;

      eventSource = new EventSource(url);

      eventSource.addEventListener('quotes', (event) => {
        // Reset retry count on successful message
        retryCount = 0;
        
        // Double-check market is still open before updating
        if (!isMarketOpen(exchange)) {
          return;
        }
        
        try {
          const data = JSON.parse(event.data) as {
            quotes: Array<{
              symbol: string;
              currentPrice?: number;
              openPrice?: number;
              highPrice?: number;
              lowPrice?: number;
            }>;
          };

          const quote = data.quotes.find(
            (q) => q.symbol.toUpperCase() === symbol.toUpperCase()
          );

          if (quote && candleSeriesRef.current && typeof quote.currentPrice === 'number' && quote.currentPrice > 0) {
            const price = quote.currentPrice;
            const nowMs = Date.now();
            const intervalSec = intervalMs.current / 1000;
            
            // Calculate candle time aligned to interval
            const candleTime = Math.floor(nowMs / intervalMs.current) * Math.floor(intervalSec) as Time;
            
            // Get or create candle data
            const lastCandle = lastCandleRef.current;
            const candleTimeNum = candleTime as number;
            
            if (lastCandle?.time === candleTimeNum) {
              // Update existing candle
              const updatedCandle = {
                time: candleTimeNum,
                open: lastCandle.open,
                high: Math.max(lastCandle.high, price),
                low: Math.min(lastCandle.low, price),
                close: price,
              };
              candleSeriesRef.current.update({ ...updatedCandle, time: candleTime });
              lastCandleRef.current = updatedCandle;
            } else {
              // New candle - use price as OHLC
              const newCandle = {
                time: candleTimeNum,
                open: price,
                high: price,
                low: price,
                close: price,
              };
              candleSeriesRef.current.update({ ...newCandle, time: candleTime });
              lastCandleRef.current = newCandle;
            }

            setLastPrice(price);
            onPriceUpdateRef.current?.(price);
          }
        } catch {
          // Ignore parse errors
        }
      });

      eventSource.onerror = () => {
        eventSource?.close();
        
        // Exponential backoff reconnect
        if (retryCount < MAX_RETRIES) {
          const delay = Math.min(1000 * Math.pow(2, retryCount), 15000);
          retryCount++;
          reconnectTimeout = setTimeout(connect, delay);
        }
      };
    };

    connect();

    return () => {
      if (reconnectTimeout) clearTimeout(reconnectTimeout);
      eventSource?.close();
    };
  }, [symbol, exchange, marketOpen]);

  return (
    <div className={`relative w-full ${className}`}>
      {/* Controls */}
      {showControls && (
        <div className="flex items-center justify-between mb-3 flex-wrap gap-2">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-sm font-semibold text-foreground">{symbol}</span>
            {lastPrice !== null && (
              <span className="text-sm font-mono text-muted-foreground">
                {formatPrice(lastPrice, exchange)}
              </span>
            )}
            {/* Market Status Indicator */}
            <span className={`inline-flex items-center gap-1 px-2 py-0.5 text-[10px] font-medium rounded-full ${
              marketOpen 
                ? 'bg-green-500/10 text-green-500 border border-green-500/20' 
                : 'bg-red-500/10 text-red-500 border border-red-500/20'
            }`}>
              <span className={`w-1.5 h-1.5 rounded-full ${marketOpen ? 'bg-green-500 animate-pulse' : 'bg-red-500'}`} />
              {marketOpen ? 'LIVE' : 'CLOSED'}
            </span>
            {/* Timezone indicator */}
            <span className="text-[10px] text-muted-foreground">
              ({getTimezoneAbbr(exchange)})
            </span>
          </div>
          <div className="flex gap-1">
            {(Object.keys(RANGE_CONFIG) as TimeRange[]).map((r) => (
              <button
                key={r}
                onClick={() => setRange(r)}
                className={`px-3 py-1 text-xs font-medium rounded transition-colors ${
                  range === r
                    ? 'bg-yellow-500/20 text-yellow-500 border border-yellow-500/30'
                    : 'bg-muted/30 text-muted-foreground hover:bg-muted/50 border border-transparent'
                }`}
              >
                {RANGE_CONFIG[r].label}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Chart Container - flexible height */}
      <div
        ref={chartContainerRef}
        className="relative rounded-lg overflow-hidden bg-card/30 border border-border/30 w-full"
        style={{ height, minHeight: 300 }}
      >
        {loading && (
          <div className="absolute inset-0 flex items-center justify-center bg-background/80 z-10">
            <TradingLoader />
          </div>
        )}
        {error && !loading && (
          <div className="absolute inset-0 flex items-center justify-center bg-background/80 z-10">
            <div className="text-center">
              <p className="text-red-500 text-sm">{error}</p>
              <button
                onClick={fetchData}
                className="mt-2 px-3 py-1 text-xs bg-muted hover:bg-muted/80 rounded"
              >
                Retry
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
