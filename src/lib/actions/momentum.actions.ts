'use server';

import yahooFinance from 'yahoo-finance2';
import type { MarketType } from '@/lib/markets';
import { getStocksForMarket } from '@/lib/stocks/getStocksForMarket';

const yf = new yahooFinance({
  suppressNotices: ['yahooSurvey'],
  validation: { logErrors: false },
});

// ============================================================================
// TYPE DEFINITIONS
// ============================================================================

interface Candle {
  timestamp: number;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

type YahooQuote = {
  symbol?: string;
  shortName?: string;
  longName?: string;
  regularMarketPrice?: number;
  regularMarketOpen?: number;
  regularMarketChangePercent?: number;
  regularMarketVolume?: number;
  averageDailyVolume10Day?: number;
  averageDailyVolume3Month?: number;
  regularMarketDayHigh?: number;
  regularMarketDayLow?: number;
  fiftyTwoWeekHigh?: number;
  fiftyTwoWeekLow?: number;
  regularMarketTime?: number;
  marketCap?: number;
};

export type MomentumSignalType = 'Bullish Breakout' | 'Bearish Breakdown';

export type BreakoutSignal = {
  signal: 'BULLISH' | 'BEARISH' | 'NEUTRAL';
  reason: string;
  confidenceScore: number;
  breakoutPrice: number;
  breakoutTime: number;
  signalPercent: number; // Day % change at breakout time (frozen snapshot)
};

export type MomentumRadarItem = {
  symbol: string;
  name: string;
  sector: string;
  signalType: MomentumSignalType;
  breakoutPrice: number;
  signalStrength: number;
  volumeMultiple: string;
  breakoutTime: number;
  signalPercent: number;
  rsi: number;
  change15Min: number;
  priceHistory: number[];
  currentPrice: number;
  marketCap?: number;
  reason: string;
  confidenceScore: number;
  market: 'US' | 'IN'; // For timezone formatting in UI
};

// ============================================================================
// UTILITY FUNCTIONS
// ============================================================================

const chunkArray = <T,>(items: T[], chunkSize: number): T[][] => {
  if (chunkSize <= 0) return [items];
  const out: T[][] = [];
  for (let i = 0; i < items.length; i += chunkSize) out.push(items.slice(i, i + chunkSize));
  return out;
};

const toNumber = (value: unknown): number | undefined => {
  return typeof value === 'number' && Number.isFinite(value) ? value : undefined;
};

const isTooManyRequestsError = (error: unknown): boolean => {
  if (!error || typeof error !== 'object') return false;
  const e = error as { code?: unknown; message?: unknown };
  if (e.code === 429) return true;
  if (typeof e.message === 'string' && /too many requests|\b429\b/i.test(e.message)) return true;
  return false;
};

const formatMultiple = (multiple: number): string => {
  if (!Number.isFinite(multiple) || multiple <= 0) return '0x';
  const rounded = Math.round(multiple * 10) / 10;
  return `${rounded.toFixed(1)}x`;
};

const normalizeSymbol = (raw: string): string => {
  const s = String(raw ?? '').trim().toUpperCase();
  if (!s) return '';
  return s.replace(/\.(BO|NS)$/i, '');
};

// ============================================================================
// TECHNICAL INDICATOR CALCULATIONS
// ============================================================================

/**
 * Calculate Simple Moving Average (SMA)
 */
const calculateSMA = (data: number[], period: number): number[] => {
  if (data.length < period) return [];
  
  const sma: number[] = [];
  let sum = 0;
  
  // Calculate first SMA
  for (let i = 0; i < period; i++) {
    sum += data[i];
  }
  sma.push(sum / period);
  
  // Calculate remaining SMAs using sliding window
  for (let i = period; i < data.length; i++) {
    sum = sum - data[i - period] + data[i];
    sma.push(sum / period);
  }
  
  return sma;
};

/**
 * Calculate True Range for a single candle
 */
const calculateTrueRange = (current: Candle, previous: Candle | null): number => {
  const highLow = current.high - current.low;
  
  if (!previous) return highLow;
  
  const highClose = Math.abs(current.high - previous.close);
  const lowClose = Math.abs(current.low - previous.close);
  
  return Math.max(highLow, highClose, lowClose);
};

/**
 * Calculate Average True Range (ATR) with period 14
 */
const calculateATR = (candles: Candle[], period: number = 14): number[] => {
  if (candles.length < period + 1) return [];
  
  const trueRanges: number[] = [];
  
  // Calculate True Range for each candle
  for (let i = 0; i < candles.length; i++) {
    const tr = calculateTrueRange(candles[i], i > 0 ? candles[i - 1] : null);
    trueRanges.push(tr);
  }
  
  // Calculate ATR using Wilder's smoothing
  const atr: number[] = [];
  
  // First ATR is simple average of first 'period' true ranges
  let sum = 0;
  for (let i = 0; i < period; i++) {
    sum += trueRanges[i];
  }
  let currentATR = sum / period;
  atr.push(currentATR);
  
  // Subsequent ATRs use Wilder's smoothing
  for (let i = period; i < trueRanges.length; i++) {
    currentATR = ((currentATR * (period - 1)) + trueRanges[i]) / period;
    atr.push(currentATR);
  }
  
  return atr;
};

/**
 * Calculate Relative Volume (RVOL)
 * RVOL = Current Volume / SMA(Volume, 20)
 */
const calculateRVOL = (volumes: number[], period: number = 20): number => {
  if (volumes.length < period) return 1;
  
  const currentVolume = volumes.at(-1) ?? 0;
  const avgVolume = volumes.slice(-period - 1, -1).reduce((a, b) => a + b, 0) / period;
  
  if (avgVolume <= 0) return 1;
  return currentVolume / avgVolume;
};

/**
 * Calculate Linear Regression Slope
 * This measures the acceleration/direction of the trend
 * Positive slope = upward trajectory, Negative slope = downward trajectory
 */
const calculateLinearRegressionSlope = (data: number[], period: number = 20): number => {
  if (data.length < period) return 0;
  
  const slice = data.slice(-period);
  const n = slice.length;
  
  // Calculate means
  let sumX = 0;
  let sumY = 0;
  let sumXY = 0;
  let sumXX = 0;
  
  for (let i = 0; i < n; i++) {
    sumX += i;
    sumY += slice[i];
    sumXY += i * slice[i];
    sumXX += i * i;
  }
  
  const denominator = (n * sumXX) - (sumX * sumX);
  if (denominator === 0) return 0;
  
  const slope = ((n * sumXY) - (sumX * sumY)) / denominator;
  
  // Normalize slope as percentage of average price
  const avgPrice = sumY / n;
  if (avgPrice === 0) return 0;
  
  return (slope / avgPrice) * 100; // Return as percentage change per bar
};

/**
 * Calculate RSI using Wilder's Smoothing (period 14)
 */
const calculateRSI = (closes: number[], period: number = 14): number => {
  if (closes.length < period + 1) return 50;
  
  const changes: number[] = [];
  for (let i = 1; i < closes.length; i++) {
    changes.push(closes[i] - closes[i - 1]);
  }
  
  if (changes.length < period) return 50;
  
  let avgGain = 0;
  let avgLoss = 0;
  
  // First calculation: simple average
  for (let i = 0; i < period; i++) {
    if (changes[i] > 0) avgGain += changes[i];
    else avgLoss += Math.abs(changes[i]);
  }
  
  avgGain /= period;
  avgLoss /= period;
  
  // Apply Wilder's Smoothing
  for (let i = period; i < changes.length; i++) {
    const gain = Math.max(0, changes[i]);
    const loss = Math.max(0, -changes[i]);
    
    avgGain = ((avgGain * (period - 1)) + gain) / period;
    avgLoss = ((avgLoss * (period - 1)) + loss) / period;
  }
  
  if (avgLoss === 0) return 100;
  
  const rs = avgGain / avgLoss;
  return 100 - (100 / (1 + rs));
};

// ============================================================================
// INSTITUTIONAL FLOW ANALYSIS
// ============================================================================

/**
 * Analyze institutional buying/selling pressure
 * Big players = high volume candles. Track if they're buying (price up on volume) or selling (price down on volume)
 * 
 * Returns: 
 *   buyingPressure: percentage of volume that was buying (0-100)
 *   sellingPressure: percentage of volume that was selling (0-100)
 *   netFlow: positive = net buying, negative = net selling
 *   consecutiveBuying: number of consecutive candles with net buying
 *   consecutiveSelling: number of consecutive candles with net selling
 */
const analyzeInstitutionalFlow = (candles: Candle[]): {
  buyingPressure: number;
  sellingPressure: number;
  netFlow: number;
  consecutiveBuying: number;
  consecutiveSelling: number;
  bigPlayersBuying: boolean;
  bigPlayersSelling: boolean;
} => {
  if (candles.length < 5) {
    return { buyingPressure: 50, sellingPressure: 50, netFlow: 0, consecutiveBuying: 0, consecutiveSelling: 0, bigPlayersBuying: false, bigPlayersSelling: false };
  }

  const avgVolume = candles.reduce((sum, c) => sum + c.volume, 0) / candles.length;
  
  let totalBuyingVolume = 0;
  let totalSellingVolume = 0;
  let consecutiveBuying = 0;
  let consecutiveSelling = 0;
  let currentBuyingStreak = 0;
  let currentSellingStreak = 0;
  
  // Analyze each candle for buying vs selling pressure
  // If candle closes higher than it opens AND has above-average volume = institutional buying
  // If candle closes lower than it opens AND has above-average volume = institutional selling
  for (const candle of candles) {
    const isBullishCandle = candle.close > candle.open;
    const isBearishCandle = candle.close < candle.open;
    const isHighVolume = candle.volume > avgVolume * 1.2; // 20% above average = significant
    
    // Calculate buying/selling volume using candle body ratio
    const bodySize = Math.abs(candle.close - candle.open);
    const totalRange = candle.high - candle.low;
    const bodyRatio = totalRange > 0 ? bodySize / totalRange : 0.5;
    
    if (isBullishCandle) {
      // Buying pressure: use body ratio and volume
      const buyVol = candle.volume * (0.5 + bodyRatio * 0.5);
      totalBuyingVolume += buyVol;
      totalSellingVolume += candle.volume - buyVol;
      
      if (isHighVolume) {
        currentBuyingStreak++;
        currentSellingStreak = 0;
      }
    } else if (isBearishCandle) {
      // Selling pressure
      const sellVol = candle.volume * (0.5 + bodyRatio * 0.5);
      totalSellingVolume += sellVol;
      totalBuyingVolume += candle.volume - sellVol;
      
      if (isHighVolume) {
        currentSellingStreak++;
        currentBuyingStreak = 0;
      }
    } else {
      // Doji - neutral, split 50/50
      totalBuyingVolume += candle.volume * 0.5;
      totalSellingVolume += candle.volume * 0.5;
    }
    
    consecutiveBuying = Math.max(consecutiveBuying, currentBuyingStreak);
    consecutiveSelling = Math.max(consecutiveSelling, currentSellingStreak);
  }
  
  const totalVolume = totalBuyingVolume + totalSellingVolume;
  const buyingPressure = totalVolume > 0 ? (totalBuyingVolume / totalVolume) * 100 : 50;
  const sellingPressure = totalVolume > 0 ? (totalSellingVolume / totalVolume) * 100 : 50;
  const netFlow = buyingPressure - sellingPressure;
  
  // Big players are continuously buying if we see 3+ consecutive high-volume bullish candles
  const bigPlayersBuying = consecutiveBuying >= 3 && buyingPressure > 55;
  const bigPlayersSelling = consecutiveSelling >= 3 && sellingPressure > 55;
  
  return {
    buyingPressure,
    sellingPressure,
    netFlow,
    consecutiveBuying,
    consecutiveSelling,
    bigPlayersBuying,
    bigPlayersSelling,
  };
};

// ============================================================================
// TIMEZONE & MARKET SESSION UTILITIES
// ============================================================================

/**
 * Get the market session start time in milliseconds for a given market
 * US Market: 9:30 AM EST (14:30 UTC, 8:00 PM IST)
 * Indian Market: 9:15 AM IST (3:45 UTC)
 * 
 * This returns the MOST RECENT trading session start, which could be:
 * - Today if market is open or has been open today
 * - Yesterday/last trading day if market hasn't opened yet today
 */
const getMarketSessionStart = (market: MarketType): number => {
  const now = new Date();
  
  if (market === 'US') {
    // US market opens at 9:30 AM EST
    // Use Intl.DateTimeFormat for accurate timezone handling
    const estFormatter = new Intl.DateTimeFormat('en-US', {
      timeZone: 'America/New_York',
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      hour12: false,
    });
    
    const parts = estFormatter.formatToParts(now);
    const estYear = parseInt(parts.find(p => p.type === 'year')?.value ?? '2026');
    const estMonth = parseInt(parts.find(p => p.type === 'month')?.value ?? '1') - 1;
    const estDay = parseInt(parts.find(p => p.type === 'day')?.value ?? '1');
    const estHour = parseInt(parts.find(p => p.type === 'hour')?.value ?? '0');
    const estMinute = parseInt(parts.find(p => p.type === 'minute')?.value ?? '0');
    
    // Create session start at 9:30 AM EST for today (in EST context)
    // We need to use a date string approach to get accurate EST time
    const todayStr = `${estYear}-${String(estMonth + 1).padStart(2, '0')}-${String(estDay).padStart(2, '0')}`;
    
    // If current EST time is before 9:30 AM, use the previous trading day
    // Also account for the fact that we want to show the WHOLE day's data
    let sessionDate = todayStr;
    if (estHour < 9 || (estHour === 9 && estMinute < 30)) {
      // Before market open - use yesterday
      const yesterday = new Date(now);
      yesterday.setDate(yesterday.getDate() - 1);
      const ydParts = estFormatter.formatToParts(yesterday);
      const ydYear = ydParts.find(p => p.type === 'year')?.value ?? '2026';
      const ydMonth = ydParts.find(p => p.type === 'month')?.value ?? '01';
      const ydDay = ydParts.find(p => p.type === 'day')?.value ?? '01';
      sessionDate = `${ydYear}-${ydMonth}-${ydDay}`;
    }
    
    // Create the session start timestamp: 9:30 AM EST on sessionDate
    // Parse as EST using Date constructor with timezone offset
    const sessionStartEST = new Date(`${sessionDate}T09:30:00-05:00`);
    
    console.log(`[US Session] EST Now: ${estHour}:${estMinute.toString().padStart(2,'0')}, Session Date: ${sessionDate}`);
    
    return sessionStartEST.getTime();
  } else {
    // Indian market opens at 9:15 AM IST
    const istFormatter = new Intl.DateTimeFormat('en-US', {
      timeZone: 'Asia/Kolkata',
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      hour12: false,
    });
    
    const parts = istFormatter.formatToParts(now);
    const istYear = parseInt(parts.find(p => p.type === 'year')?.value ?? '2026');
    const istMonth = parseInt(parts.find(p => p.type === 'month')?.value ?? '1') - 1;
    const istDay = parseInt(parts.find(p => p.type === 'day')?.value ?? '1');
    const istHour = parseInt(parts.find(p => p.type === 'hour')?.value ?? '0');
    const istMinute = parseInt(parts.find(p => p.type === 'minute')?.value ?? '0');
    
    const todayStr = `${istYear}-${String(istMonth + 1).padStart(2, '0')}-${String(istDay).padStart(2, '0')}`;
    
    let sessionDate = todayStr;
    if (istHour < 9 || (istHour === 9 && istMinute < 15)) {
      // Before market open - use yesterday
      const yesterday = new Date(now);
      yesterday.setDate(yesterday.getDate() - 1);
      const ydParts = istFormatter.formatToParts(yesterday);
      const ydYear = ydParts.find(p => p.type === 'year')?.value ?? '2026';
      const ydMonth = ydParts.find(p => p.type === 'month')?.value ?? '01';
      const ydDay = ydParts.find(p => p.type === 'day')?.value ?? '01';
      sessionDate = `${ydYear}-${ydMonth}-${ydDay}`;
    }
    
    // Create the session start timestamp: 9:15 AM IST on sessionDate
    const sessionStartIST = new Date(`${sessionDate}T09:15:00+05:30`);
    
    // Only log once per session
    return sessionStartIST.getTime();
  }
};

/**
 * Find ALL momentum breakouts during today's trading session
 * This scans ALL candles and finds EVERY breakout that occurred (not just the first/current)
 * 
 * This allows us to show stocks that had momentum earlier in the day even if 
 * they've since returned to normal
 */
type BreakoutPoint = {
  time: number;
  price: number;
  type: 'BULLISH' | 'BEARISH';
  index: number;
  strength: number; // How strong the breakout was (% above/below the range)
};

const findAllBreakoutsInSession = (candles: Candle[], market: MarketType): BreakoutPoint[] => {
  if (candles.length < 25) {
    return [];
  }

  // Get today's market session start based on market timezone
  const sessionStart = getMarketSessionStart(market);
  
  // Find where today's session candles start
  let sessionStartIndex = -1;
  for (let i = 0; i < candles.length; i++) {
    if (candles[i].timestamp >= sessionStart) {
      sessionStartIndex = i;
      break;
    }
  }
  
  // If we don't have session candles, use the last portion
  if (sessionStartIndex < 0) {
    sessionStartIndex = Math.max(0, candles.length - 100);
  }
  
  // Need at least 20 candles before we start checking for breakouts
  const startIdx = Math.max(sessionStartIndex, 20);
  
  const breakouts: BreakoutPoint[] = [];
  let lastBreakoutType: 'BULLISH' | 'BEARISH' | null = null;
  let candlesSinceLastBreakout = 0;
  
  for (let i = startIdx; i < candles.length; i++) {
    const currentCandle = candles[i];
    const currentClose = currentCandle.close;
    
    // Get the 20-period high/low BEFORE this candle
    const prev20Highs = candles.slice(i - 20, i).map(c => c.high);
    const prev20Lows = candles.slice(i - 20, i).map(c => c.low);
    const prev20High = Math.max(...prev20Highs);
    const prev20Low = Math.min(...prev20Lows);
    const range = prev20High - prev20Low;
    
    candlesSinceLastBreakout++;
    
    // Check for bullish breakout
    if (currentClose > prev20High) {
      const strength = range > 0 ? ((currentClose - prev20High) / range) * 100 : 0;
      
      // Only record if it's a new type of breakout OR enough time has passed (6+ candles = 30 min)
      if (lastBreakoutType !== 'BULLISH' || candlesSinceLastBreakout >= 6) {
        breakouts.push({
          time: currentCandle.timestamp,
          price: currentClose,
          type: 'BULLISH',
          index: i,
          strength,
        });
        lastBreakoutType = 'BULLISH';
        candlesSinceLastBreakout = 0;
      }
    }
    
    // Check for bearish breakdown
    if (currentClose < prev20Low) {
      const strength = range > 0 ? ((prev20Low - currentClose) / range) * 100 : 0;
      
      // Only record if it's a new type of breakout OR enough time has passed
      if (lastBreakoutType !== 'BEARISH' || candlesSinceLastBreakout >= 6) {
        breakouts.push({
          time: currentCandle.timestamp,
          price: currentClose,
          type: 'BEARISH',
          index: i,
          strength,
        });
        lastBreakoutType = 'BEARISH';
        candlesSinceLastBreakout = 0;
      }
    }
  }
  
  return breakouts;
};

/**
 * Find the STRONGEST/MOST SIGNIFICANT momentum change point in today's session
 * This picks the best breakout from all detected breakouts
 */
const findMomentumChangePoint = (candles: Candle[], market: MarketType): {
  changeTime: number;
  changePrice: number;
  changeType: 'BULLISH' | 'BEARISH' | 'NONE';
  changeIndex: number;
} => {
  const allBreakouts = findAllBreakoutsInSession(candles, market);
  
  if (allBreakouts.length === 0) {
    return { changeTime: 0, changePrice: 0, changeType: 'NONE', changeIndex: -1 };
  }
  
  // Find the strongest breakout (highest strength value)
  // If strengths are similar, prefer more recent breakouts
  let bestBreakout = allBreakouts[0];
  
  for (const breakout of allBreakouts) {
    // If this breakout is significantly stronger, use it
    if (breakout.strength > bestBreakout.strength + 10) {
      bestBreakout = breakout;
    }
    // If strength is similar but more recent, prefer it (recency bias for active trades)
    else if (breakout.strength >= bestBreakout.strength * 0.8 && breakout.time > bestBreakout.time) {
      bestBreakout = breakout;
    }
  }
  
  return {
    changeTime: bestBreakout.time,
    changePrice: bestBreakout.price,
    changeType: bestBreakout.type,
    changeIndex: bestBreakout.index,
  };
};

// ============================================================================
// HYBRID BREAKOUT DETECTION ENGINE
// ============================================================================

/**
 * BREAKOUT DETECTION ENGINE v2
 * 
 * Purpose: Detect when momentum FIRST changed during the day and calculate confidence
 * based on institutional buying/selling activity.
 * 
 * KEY PRINCIPLES:
 * 1. DETECT THE FIRST BREAKOUT OF THE DAY - not just the current state
 * 2. Track INSTITUTIONAL FLOW - if big players are continuously buying = high confidence bullish
 * 3. Track INSTITUTIONAL FLOW - if big players are continuously selling = high confidence bearish
 * 4. Show PRECISE TIMING of when momentum changed
 * 
 * CONFIDENCE SCORE = Probability that price will continue in the detected direction:
 * - Based on whether institutions (big volume) are buying or selling
 * - Continuous buying pressure = high bullish confidence
 * - Continuous selling pressure = high bearish confidence
 */
export async function detectBreakout(candles: Candle[], previousClose?: number, market: MarketType = 'US'): Promise<BreakoutSignal> {
  const minDataPoints = 30;

  if (candles.length < minDataPoints) {
    return {
      signal: 'NEUTRAL',
      reason: 'Insufficient data for analysis',
      confidenceScore: 0,
      breakoutPrice: 0,
      breakoutTime: 0,
      signalPercent: 0,
    };
  }

  const closes = candles.map((c) => c.close);
  const volumes = candles.map((c) => c.volume);

  // =========================================================================
  // STEP 1: Find when momentum FIRST changed during the trading session
  // Uses the market parameter to determine correct session times
  // =========================================================================
  const momentumChange = findMomentumChangePoint(candles, market);
  
  if (momentumChange.changeType === 'NONE') {
    return {
      signal: 'NEUTRAL',
      reason: 'No momentum change detected today',
      confidenceScore: 0,
      breakoutPrice: 0,
      breakoutTime: 0,
      signalPercent: 0,
    };
  }

  // =========================================================================
  // STEP 2: Analyze institutional flow AFTER the momentum change
  // This tells us if big players are continuously buying or selling
  // =========================================================================
  const candlesAfterChange = candles.slice(momentumChange.changeIndex);
  const institutionalFlow = analyzeInstitutionalFlow(candlesAfterChange);
  
  // =========================================================================
  // STEP 3: Determine signal based on momentum change AND institutional flow
  // =========================================================================
  const signal: 'BULLISH' | 'BEARISH' = momentumChange.changeType;
  
  // If institutional flow contradicts the momentum change significantly, 
  // confidence will be adjusted in the calculation below
  // e.g., Bullish breakout but institutions are heavily selling = lower confidence

  // =========================================================================
  // STEP 4: Calculate technical indicators for additional context
  // =========================================================================
  const sma20Array = calculateSMA(closes, 20);
  const sma50Array = calculateSMA(closes, 50);
  const sma20 = sma20Array.at(-1) ?? 0;
  const sma50 = sma50Array.length > 0 ? (sma50Array.at(-1) ?? sma20) : sma20;

  const atrArray = calculateATR(candles, 14);
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  const _currentATR = atrArray.length > 0 ? (atrArray.at(-1) ?? 0) : 0;

  const rvol = calculateRVOL(volumes, 20);
  const lrSlope = calculateLinearRegressionSlope(closes, 20);
  const rsi = calculateRSI(closes, 14);

  const currentClose = candles.at(-1)!.close;
  const breakoutPrice = momentumChange.changePrice;
  const breakoutTime = momentumChange.changeTime;
  
  // Calculate how much price moved since the breakout
  const moveSinceBreakout = ((currentClose - breakoutPrice) / breakoutPrice) * 100;
  const isBullish = signal === 'BULLISH';

  // =========================================================================
  // CONFIDENCE CALCULATION v2
  // Based primarily on INSTITUTIONAL FLOW + technical confirmation
  // =========================================================================
  
  const reasons: string[] = [];
  let confidence = 25; // Base confidence for detected breakout

  // 1. INSTITUTIONAL FLOW (0-35 points) - THE MOST IMPORTANT FACTOR
  // If big players are continuously buying → high probability of going UP
  // If big players are continuously selling → high probability of going DOWN
  if (isBullish) {
    if (institutionalFlow.bigPlayersBuying) {
      confidence += 35;
      reasons.push(`Institutions Buying (${institutionalFlow.consecutiveBuying}×)`);
    } else if (institutionalFlow.buyingPressure > 60) {
      confidence += 25;
      reasons.push(`Buy Pressure ${institutionalFlow.buyingPressure.toFixed(0)}%`);
    } else if (institutionalFlow.buyingPressure > 52) {
      confidence += 15;
      reasons.push(`Buying ${institutionalFlow.buyingPressure.toFixed(0)}%`);
    } else if (institutionalFlow.bigPlayersSelling) {
      confidence -= 20;
      reasons.push(`⚠️ Institutions Selling`);
    } else {
      reasons.push(`Flow: ${institutionalFlow.netFlow > 0 ? '+' : ''}${institutionalFlow.netFlow.toFixed(0)}%`);
    }
  } else {
    // Bearish signal
    if (institutionalFlow.bigPlayersSelling) {
      confidence += 35;
      reasons.push(`Institutions Selling (${institutionalFlow.consecutiveSelling}×)`);
    } else if (institutionalFlow.sellingPressure > 60) {
      confidence += 25;
      reasons.push(`Sell Pressure ${institutionalFlow.sellingPressure.toFixed(0)}%`);
    } else if (institutionalFlow.sellingPressure > 52) {
      confidence += 15;
      reasons.push(`Selling ${institutionalFlow.sellingPressure.toFixed(0)}%`);
    } else if (institutionalFlow.bigPlayersBuying) {
      confidence -= 20;
      reasons.push(`⚠️ Institutions Buying`);
    } else {
      reasons.push(`Flow: ${institutionalFlow.netFlow > 0 ? '+' : ''}${institutionalFlow.netFlow.toFixed(0)}%`);
    }
  }

  // 2. PRICE CONFIRMATION (0-20 points)
  // If price is moving in the direction of the breakout = confirmation
  if (isBullish && moveSinceBreakout > 0.5) {
    confidence += 20;
    reasons.push(`+${moveSinceBreakout.toFixed(1)}% since breakout`);
  } else if (isBullish && moveSinceBreakout > 0) {
    confidence += 10;
    reasons.push(`+${moveSinceBreakout.toFixed(2)}% confirmed`);
  } else if (!isBullish && moveSinceBreakout < -0.5) {
    confidence += 20;
    reasons.push(`${moveSinceBreakout.toFixed(1)}% since breakdown`);
  } else if (!isBullish && moveSinceBreakout < 0) {
    confidence += 10;
    reasons.push(`${moveSinceBreakout.toFixed(2)}% confirmed`);
  } else {
    // Price moved opposite to breakout direction
    confidence -= 15;
    reasons.push(`Price reverting`);
  }

  // 3. VOLUME CONFIRMATION (0-15 points)
  if (rvol >= 2.5) {
    confidence += 15;
    reasons.push(`Vol ${rvol.toFixed(1)}×`);
  } else if (rvol >= 1.5) {
    confidence += 10;
    reasons.push(`Vol ${rvol.toFixed(1)}×`);
  } else if (rvol >= 1.2) {
    confidence += 5;
  } else if (rvol < 0.8) {
    confidence -= 5;
    reasons.push(`Low Vol`);
  }

  // 4. TREND ALIGNMENT (0-10 points)
  const bullishTrend = sma20 > sma50;
  const bearishTrend = sma20 < sma50;
  
  if ((isBullish && bullishTrend) || (!isBullish && bearishTrend)) {
    confidence += 10;
    reasons.push(isBullish ? 'Trend ↑' : 'Trend ↓');
  } else if ((isBullish && bearishTrend) || (!isBullish && bullishTrend)) {
    confidence -= 5;
    reasons.push('Counter-Trend');
  }

  // 5. MOMENTUM (0-10 points)
  const bullishSlope = lrSlope > 0;
  const bearishSlope = lrSlope < 0;
  
  if ((isBullish && bullishSlope) || (!isBullish && bearishSlope)) {
    confidence += 10;
    reasons.push(isBullish ? 'Mom ↑' : 'Mom ↓');
  }

  // 6. RSI CHECK (prevent exhaustion)
  if (isBullish && rsi > 80) {
    confidence -= 10;
    reasons.push(`RSI ${Math.round(rsi)} OB`);
  } else if (!isBullish && rsi < 20) {
    confidence -= 10;
    reasons.push(`RSI ${Math.round(rsi)} OS`);
  }

  // Clamp confidence between 15 and 95
  confidence = Math.max(15, Math.min(95, confidence));

  // Calculate signal percent (day's change at breakout time)
  let signalPercent = 0;
  if (typeof previousClose === 'number' && previousClose > 0) {
    signalPercent = ((breakoutPrice - previousClose) / previousClose) * 100;
  }

  return {
    signal,
    reason: reasons.join(' • '),
    confidenceScore: Math.round(confidence),
    breakoutPrice,
    breakoutTime,
    signalPercent,
  };
}

// ============================================================================
// DATA FETCHING FUNCTIONS
// ============================================================================

const getYahooQuoteBatch = async (symbols: string[]): Promise<YahooQuote[]> => {
  if (symbols.length === 0) return [];
  const yahoo = yf as unknown as { quote: (ticker: string | string[]) => Promise<unknown> };
  const res = await yahoo.quote(symbols.length === 1 ? symbols[0] : symbols);
  const arr = Array.isArray(res) ? (res as YahooQuote[]) : ([res as YahooQuote] as YahooQuote[]);
  return arr.filter((q) => q && typeof q === 'object');
};

const getSectorForSymbol = async (symbol: string): Promise<string> => {
  try {
    const summary = await yf.quoteSummary(symbol, { modules: ['summaryProfile'] });
    const sector = (summary as unknown as { summaryProfile?: { sector?: unknown } }).summaryProfile?.sector;
    if (typeof sector === 'string' && sector.trim()) return sector.trim();
  } catch {
    // ignore
  }
  return 'Miscellaneous';
};

/**
 * Fetch intraday 5-minute candles for hybrid breakout detection
 */
const fetchIntradayCandles = async (symbol: string): Promise<Candle[]> => {
  const period2 = new Date();
  const period1 = new Date(period2.getTime() - 5 * 24 * 60 * 60 * 1000); // Last 5 days

  try {
    const chart = (await yf.chart(symbol, {
      period1,
      period2,
      interval: '5m',
      return: 'object',
    })) as unknown as {
      timestamp?: number[];
      indicators?: { 
        quote?: Array<{ 
          open: Array<number | null>; 
          high: Array<number | null>; 
          low: Array<number | null>; 
          close: Array<number | null>;
          volume: Array<number | null>;
        }> 
      };
    };

    const timestamps = Array.isArray(chart?.timestamp) ? chart.timestamp : [];
    const quote0 = Array.isArray(chart?.indicators?.quote) ? chart.indicators.quote[0] : undefined;
    const opens = quote0?.open ?? [];
    const highs = quote0?.high ?? [];
    const lows = quote0?.low ?? [];
    const closes = quote0?.close ?? [];
    const volumes = quote0?.volume ?? [];

    const candles: Candle[] = [];
    
    for (let i = 0; i < timestamps.length; i++) {
      const ts = timestamps[i];
      const open = opens[i];
      const high = highs[i];
      const low = lows[i];
      const close = closes[i];
      const volume = volumes[i];
      
      // Skip invalid candles
      if (
        typeof ts !== 'number' || !Number.isFinite(ts) ||
        typeof open !== 'number' || !Number.isFinite(open) ||
        typeof high !== 'number' || !Number.isFinite(high) ||
        typeof low !== 'number' || !Number.isFinite(low) ||
        typeof close !== 'number' || !Number.isFinite(close) ||
        typeof volume !== 'number' || !Number.isFinite(volume)
      ) {
        continue;
      }
      
      candles.push({
        timestamp: ts * 1000,
        open,
        high,
        low,
        close,
        volume,
      });
    }

    candles.sort((a, b) => a.timestamp - b.timestamp);
    return candles;
  } catch (error) {
    if (isTooManyRequestsError(error)) throw error;
    return [];
  }
};

const fetchYahooQuotesForSymbols = async (symbols: string[]): Promise<Map<string, YahooQuote>> => {
  const quoteChunks = chunkArray(symbols, 50);
  const quotes: YahooQuote[] = [];

  for (const chunk of quoteChunks) {
    try {
      const res = await getYahooQuoteBatch(chunk);
      quotes.push(...res);
    } catch (error) {
      if (isTooManyRequestsError(error)) break;
    }
  }

  const quoteBySymbol = new Map<string, YahooQuote>();
  for (const q of quotes) {
    const sym = typeof q.symbol === 'string' ? q.symbol.trim() : '';
    if (!sym) continue;
    quoteBySymbol.set(sym.toUpperCase(), q);
  }

  return quoteBySymbol;
};

// ============================================================================
// HELPER FUNCTIONS FOR DISPLAY
// ============================================================================

/**
 * Calculate 15-minute price change from candles
 */
const calculate15MinChange = (candles: Candle[]): number => {
  if (candles.length < 4) return 0;
  
  const latestPrice = candles.at(-1)?.close ?? 0;
  const idx15MinAgo = Math.max(0, candles.length - 4);
  const price15MinAgo = candles[idx15MinAgo].close;
  
  if (price15MinAgo === 0) return 0;
  return ((latestPrice - price15MinAgo) / price15MinAgo) * 100;
};

/**
 * Get last 2 hours of price data for sparkline
 */
const getLast2HoursPrices = (candles: Candle[]): number[] => {
  const numPoints = 24; // 2 hours at 5-min intervals
  const recentCandles = candles.slice(-numPoints);
  return recentCandles.map(c => c.close);
};

/**
 * Get today's candles only - more flexible for early market hours
 */
const getTodayCandles = (candles: Candle[]): Candle[] => {
  if (candles.length === 0) return [];
  
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const todayStart = today.getTime();
  
  const todayCandles = candles.filter(c => c.timestamp >= todayStart);
  
  // If we have at least 30 candles today, use them
  if (todayCandles.length >= 30) {
    return todayCandles;
  }
  
  // Otherwise, use the most recent candles we have (for early market or weekends)
  // This ensures we still show signals based on recent activity
  return candles.slice(-Math.max(60, candles.length));
};

// ============================================================================
// ASYNC POOL FOR CONCURRENT PROCESSING
// ============================================================================

const asyncPool = async <T, R>(args: {
  items: T[];
  concurrency: number;
  mapper: (item: T, index: number) => Promise<R>;
}): Promise<R[]> => {
  const { items, concurrency, mapper } = args;
  const results: R[] = new Array(items.length) as R[];
  let nextIndex = 0;

  const workers = new Array(Math.max(1, concurrency)).fill(0).map(async () => {
    while (true) {
      const current = nextIndex;
      nextIndex += 1;
      if (current >= items.length) return;
      results[current] = await mapper(items[current], current);
    }
  });

  await Promise.all(workers);
  return results;
};

// ============================================================================
// MAIN EXPORT: GET MOMENTUM RADAR
// ============================================================================

export const getMomentumRadar = async (args?: {
  market?: MarketType;
  limit?: number;
}): Promise<MomentumRadarItem[]> => {
  const market: MarketType = args?.market ?? 'IN';
  // Default to 100 to show all detected stocks throughout the trading day
  const limit = typeof args?.limit === 'number' && args.limit > 0 ? Math.floor(args.limit) : 100;

  const stocks = getStocksForMarket(market);
  const bySymbol = new Map<string, { symbol: string; name: string }>();
  
  for (const s of stocks) {
    const sym = String(s.symbol ?? '').trim();
    if (!sym) continue;
    if (!bySymbol.has(sym)) bySymbol.set(sym, { symbol: sym, name: s.name ?? sym });
  }

  const universe = Array.from(bySymbol.values());
  const symbols = universe.map((s) => s.symbol);

  // 1) Fetch quotes for basic filtering
  const quoteBySymbol = await fetchYahooQuotesForSymbols(symbols);

  // 2) Pre-filter: stocks with basic volume activity
  const preFiltered: Array<{ symbol: string; name: string; quote: YahooQuote }> = [];
  
  for (const meta of universe) {
    const q = quoteBySymbol.get(meta.symbol.toUpperCase());
    if (!q) continue;

    const currentPrice = toNumber(q.regularMarketPrice);
    const volume = toNumber(q.regularMarketVolume);
    const avgVol = toNumber(q.averageDailyVolume10Day) ?? toNumber(q.averageDailyVolume3Month);

    if (
      typeof currentPrice !== 'number' ||
      typeof volume !== 'number' ||
      typeof avgVol !== 'number' ||
      avgVol <= 0 ||
      currentPrice <= 0
    ) {
      continue;
    }

    // Basic pre-filter: at least some volume activity
    const basicRVOL = volume / avgVol;
    if (basicRVOL < 0.5) continue; // Skip very low volume stocks

    preFiltered.push({ symbol: meta.symbol, name: meta.name, quote: q });
  }

  // 3) Process candidates with Hybrid Breakout Detection
  // Process more stocks to catch all momentum throughout the day
  let rateLimited = false;
  
  console.log(`[MomentumRadar] Market: ${market}, Pre-filtered: ${preFiltered.length} stocks`);
  
  const processedItems = await asyncPool({
    items: preFiltered.slice(0, 150), // Increased to 150 to catch more momentum signals
    concurrency: 5, // Increased concurrency for faster processing
    mapper: async (item) => {
      if (rateLimited) return null;
      
      try {
        // Fetch intraday candles
        const allCandles = await fetchIntradayCandles(item.symbol);
        const candles = getTodayCandles(allCandles);
        
        if (candles.length < 30) {
          return null; // Not enough data for analysis - lowered from 51
        }
        
        // Determine previous day close from quote if available (fallbacks)
        const qAny = item.quote as unknown as Record<string, unknown>;
        const rawPrevClose = qAny['regularMarketPreviousClose'] ?? qAny['previousClose'] ?? qAny['regularMarketOpen'];
        const prevClose = toNumber(rawPrevClose);

        // Run Hybrid Breakout Detection (pass previous close and market type)
        const breakoutResult = await detectBreakout(candles, prevClose, market);
        
        // Only include stocks with actual breakout signals
        if (breakoutResult.signal === 'NEUTRAL') {
          return null;
        }
        
        // Get additional data
        const sector = await getSectorForSymbol(item.symbol);
        const closes = candles.map(c => c.close);
        const volumes = candles.map(c => c.volume);
        
        const currentPrice = candles.at(-1)?.close ?? 0;
        const rsi = calculateRSI(closes, 14);
        const rvol = calculateRVOL(volumes, 20);
        const change15Min = calculate15MinChange(candles);
        const priceHistory = getLast2HoursPrices(candles);
        
        const signalType: MomentumSignalType = breakoutResult.signal === 'BULLISH' 
          ? 'Bullish Breakout' 
          : 'Bearish Breakdown';
        
        // Signal strength based on confidence and price movement
        const signalStrength = breakoutResult.signal === 'BULLISH' 
          ? Math.abs(change15Min) 
          : -Math.abs(change15Min);
        
        return {
          symbol: normalizeSymbol(item.symbol),
          name: item.name,
          sector,
          signalType,
          breakoutPrice: breakoutResult.breakoutPrice,
          signalPercent: Number.parseFloat(((breakoutResult.signalPercent ?? 0)).toFixed(2)),
          signalStrength: Number.parseFloat(signalStrength.toFixed(2)),
          volumeMultiple: formatMultiple(rvol),
          breakoutTime: breakoutResult.breakoutTime,
          rsi: Math.round(rsi),
          change15Min: Number.parseFloat(change15Min.toFixed(2)),
          priceHistory,
          currentPrice,
          marketCap: toNumber(item.quote.marketCap),
          reason: breakoutResult.reason,
          confidenceScore: breakoutResult.confidenceScore,
          market, // Include market for timezone formatting in UI
        } as MomentumRadarItem;
        
      } catch (error) {
        if (isTooManyRequestsError(error)) {
          rateLimited = true;
        }
        return null;
      }
    },
  });

  // 4) Filter and sort results - show ALL detected breakouts
  // Users can use confidence to filter themselves
  const validItems = processedItems.filter((x): x is MomentumRadarItem => 
    x !== null && x.confidenceScore > 0
  );
  
  // Sort by confidence score (highest first), then by absolute signal strength
  validItems.sort((a, b) => {
    // First by confidence
    const confDiff = b.confidenceScore - a.confidenceScore;
    if (Math.abs(confDiff) > 5) return confDiff;
    
    // Then by absolute change
    return Math.abs(b.change15Min) - Math.abs(a.change15Min);
  });

  // Return up to limit results
  const result = validItems.slice(0, limit);

  console.log(`[MomentumRadar] Market: ${market}, Detected: ${validItems.length}, Returning: ${result.length}`);

  return result;
};
