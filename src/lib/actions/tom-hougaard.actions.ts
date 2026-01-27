"use server";

/**
 * ═══════════════════════════════════════════════════════════════════════════
 *  TOM HOUGAARD'S STRATEGY - Logic Engine
 * ═══════════════════════════════════════════════════════════════════════════
 * 
 * Rules:
 * 1. FRIDAY → MONDAY: If Friday's High < Thursday's High 
 *    → Friday's Low will be visited on Monday
 * 
 * 2. WEDNESDAY → THURSDAY: If Wednesday's High < Monday's High 
 *    → Wednesday's Low will be visited on Thursday
 * 
 * This engine runs:
 * - Pre-Market: Check conditions and set target prices
 * - Real-Time: Check if target price has been hit
 * ═══════════════════════════════════════════════════════════════════════════
 */

import YahooFinance from "yahoo-finance2";

// ═══════════════════════════════════════════════════════════════════════════
//  TYPES
// ═══════════════════════════════════════════════════════════════════════════

export interface DayCandle {
  date: string;
  dayOfWeek: number; // 0=Sunday, 1=Monday, ..., 5=Friday, 6=Saturday
  dayName: string;
  open: number;
  high: number;
  low: number;
  close: number;
}

export interface TomHougaardPrediction {
  isActive: boolean;
  rule: "FRIDAY_MONDAY" | "WEDNESDAY_THURSDAY";
  ruleDescription: string;
  conditionMet: boolean;
  conditionDescription: string;
  targetPrice: number;
  targetHit: boolean;
  currentPrice: number;
  distanceToTarget: number;
  distancePercent: number;
  symbol: string;
  symbolName: string;
  referenceDay1: DayCandle; // Thursday (for rule 1) or Monday (for rule 2)
  referenceDay2: DayCandle; // Friday (for rule 1) or Wednesday (for rule 2)
  predictionDay: string; // Monday (for rule 1) or Thursday (for rule 2)
  timestamp: string;
}

export interface TomHougaardAnalysis {
  success: boolean;
  predictions: TomHougaardPrediction[];
  currentDayOfWeek: number;
  currentDayName: string;
  lastUpdated: string;
  error?: string;
}

// ═══════════════════════════════════════════════════════════════════════════
//  CONSTANTS
// ═══════════════════════════════════════════════════════════════════════════

const DAY_NAMES = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"];

// Index symbols to analyze (major indices only)
const INDEX_SYMBOLS = {
  IN: [
    { symbol: "^NSEI", name: "NIFTY 50" },
    { symbol: "^NSEBANK", name: "BANK NIFTY" },
    { symbol: "^BSESN", name: "SENSEX" },
  ],
  US: [
    { symbol: "^GSPC", name: "S&P 500" },
    { symbol: "^DJI", name: "DOW JONES" },
    { symbol: "^IXIC", name: "NASDAQ" },
  ],
};

// ═══════════════════════════════════════════════════════════════════════════
//  UTILITY FUNCTIONS
// ═══════════════════════════════════════════════════════════════════════════

const yf = new YahooFinance();

async function fetchDailyCandles(symbol: string, days: number = 10): Promise<DayCandle[]> {
  try {
    const endDate = new Date();
    const startDate = new Date();
    startDate.setDate(startDate.getDate() - days);

    const result = await yf.chart(symbol, {
      period1: startDate,
      period2: endDate,
      interval: "1d",
    });

    if (!result.quotes || result.quotes.length === 0) {
      return [];
    }

    return result.quotes
      .filter(q => q.open && q.high && q.low && q.close)
      .map(q => {
        const date = new Date(q.date);
        return {
          date: date.toISOString().split("T")[0],
          dayOfWeek: date.getDay(),
          dayName: DAY_NAMES[date.getDay()],
          open: q.open!,
          high: q.high!,
          low: q.low!,
          close: q.close!,
        };
      });
  } catch (error) {
    console.error(`Error fetching daily candles for ${symbol}:`, error);
    return [];
  }
}

async function fetchCurrentPrice(symbol: string): Promise<number | null> {
  try {
    const quote = await yf.quote(symbol);
    return quote.regularMarketPrice || null;
  } catch (error) {
    console.error(`Error fetching current price for ${symbol}:`, error);
    return null;
  }
}

function findCandleByDayOfWeek(candles: DayCandle[], targetDayOfWeek: number, weeksBack: number = 0): DayCandle | null {
  // Sort candles by date descending (most recent first)
  const sorted = [...candles].sort((a, b) => new Date(b.date).getTime() - new Date(a.date).getTime());
  
  let foundCount = 0;
  for (const candle of sorted) {
    if (candle.dayOfWeek === targetDayOfWeek) {
      if (foundCount === weeksBack) {
        return candle;
      }
      foundCount++;
    }
  }
  return null;
}

// ═══════════════════════════════════════════════════════════════════════════
//  MAIN ANALYSIS FUNCTION
// ═══════════════════════════════════════════════════════════════════════════

export async function analyzeTomHougaardStrategy(
  market: "IN" | "US" = "IN"
): Promise<TomHougaardAnalysis> {
  try {
    const now = new Date();
    const currentDayOfWeek = now.getDay();
    const currentDayName = DAY_NAMES[currentDayOfWeek];
    
    const predictions: TomHougaardPrediction[] = [];
    const symbols = INDEX_SYMBOLS[market];

    for (const { symbol, name } of symbols) {
      // Fetch last 15 days of daily candles
      const candles = await fetchDailyCandles(symbol, 15);
      if (candles.length < 5) continue;

      // Fetch current price
      const currentPrice = await fetchCurrentPrice(symbol);
      if (!currentPrice) continue;

      // ═══════════════════════════════════════════════════════════════════
      // RULE 1: FRIDAY → MONDAY
      // If Friday's High < Thursday's High → Friday's Low visited on Monday
      // ═══════════════════════════════════════════════════════════════════
      
      if (currentDayOfWeek === 1) { // Monday
        const friday = findCandleByDayOfWeek(candles, 5, 0); // Last Friday
        const thursday = findCandleByDayOfWeek(candles, 4, 0); // Last Thursday

        if (friday && thursday) {
          const conditionMet = friday.high < thursday.high;
          const targetPrice = friday.low;
          const targetHit = currentPrice <= targetPrice;
          const distanceToTarget = targetPrice - currentPrice;
          const distancePercent = (distanceToTarget / currentPrice) * 100;

          predictions.push({
            isActive: conditionMet,
            rule: "FRIDAY_MONDAY",
            ruleDescription: "Friday High < Thursday High → Friday Low will be visited on Monday",
            conditionMet,
            conditionDescription: conditionMet
              ? `✅ Friday's High (${friday.high.toFixed(2)}) < Thursday's High (${thursday.high.toFixed(2)})`
              : `❌ Friday's High (${friday.high.toFixed(2)}) ≥ Thursday's High (${thursday.high.toFixed(2)})`,
            targetPrice,
            targetHit,
            currentPrice,
            distanceToTarget,
            distancePercent,
            symbol,
            symbolName: name,
            referenceDay1: thursday,
            referenceDay2: friday,
            predictionDay: "Monday",
            timestamp: now.toISOString(),
          });
        }
      }

      // ═══════════════════════════════════════════════════════════════════
      // RULE 2: WEDNESDAY → THURSDAY
      // If Wednesday's High < Monday's High → Wednesday's Low visited on Thursday
      // ═══════════════════════════════════════════════════════════════════
      
      if (currentDayOfWeek === 4) { // Thursday
        const wednesday = findCandleByDayOfWeek(candles, 3, 0); // This Wednesday
        const monday = findCandleByDayOfWeek(candles, 1, 0); // This Monday

        if (wednesday && monday) {
          const conditionMet = wednesday.high < monday.high;
          const targetPrice = wednesday.low;
          const targetHit = currentPrice <= targetPrice;
          const distanceToTarget = targetPrice - currentPrice;
          const distancePercent = (distanceToTarget / currentPrice) * 100;

          predictions.push({
            isActive: conditionMet,
            rule: "WEDNESDAY_THURSDAY",
            ruleDescription: "Wednesday High < Monday High → Wednesday Low will be visited on Thursday",
            conditionMet,
            conditionDescription: conditionMet
              ? `✅ Wednesday's High (${wednesday.high.toFixed(2)}) < Monday's High (${monday.high.toFixed(2)})`
              : `❌ Wednesday's High (${wednesday.high.toFixed(2)}) ≥ Monday's High (${monday.high.toFixed(2)})`,
            targetPrice,
            targetHit,
            currentPrice,
            distanceToTarget,
            distancePercent,
            symbol,
            symbolName: name,
            referenceDay1: monday,
            referenceDay2: wednesday,
            predictionDay: "Thursday",
            timestamp: now.toISOString(),
          });
        }
      }

      // ═══════════════════════════════════════════════════════════════════
      // PRE-MARKET ALERTS (Show on days before prediction day)
      // ═══════════════════════════════════════════════════════════════════
      
      // On Friday/Saturday/Sunday - Preview Monday prediction
      if (currentDayOfWeek === 5 || currentDayOfWeek === 6 || currentDayOfWeek === 0) {
        const friday = findCandleByDayOfWeek(candles, 5, 0);
        const thursday = findCandleByDayOfWeek(candles, 4, 0);

        if (friday && thursday) {
          const conditionMet = friday.high < thursday.high;
          const targetPrice = friday.low;
          const distanceToTarget = targetPrice - currentPrice;
          const distancePercent = (distanceToTarget / currentPrice) * 100;

          predictions.push({
            isActive: conditionMet,
            rule: "FRIDAY_MONDAY",
            ruleDescription: "🔮 PREVIEW: Friday High < Thursday High → Friday Low will be visited on Monday",
            conditionMet,
            conditionDescription: conditionMet
              ? `✅ Friday's High (${friday.high.toFixed(2)}) < Thursday's High (${thursday.high.toFixed(2)})`
              : `❌ Friday's High (${friday.high.toFixed(2)}) ≥ Thursday's High (${thursday.high.toFixed(2)})`,
            targetPrice,
            targetHit: false,
            currentPrice,
            distanceToTarget,
            distancePercent,
            symbol,
            symbolName: name,
            referenceDay1: thursday,
            referenceDay2: friday,
            predictionDay: "Monday (upcoming)",
            timestamp: now.toISOString(),
          });
        }
      }

      // On Wednesday - Preview Thursday prediction
      if (currentDayOfWeek === 3) {
        const wednesday = findCandleByDayOfWeek(candles, 3, 0);
        const monday = findCandleByDayOfWeek(candles, 1, 0);

        if (wednesday && monday) {
          const conditionMet = wednesday.high < monday.high;
          const targetPrice = wednesday.low;
          const distanceToTarget = targetPrice - currentPrice;
          const distancePercent = (distanceToTarget / currentPrice) * 100;

          predictions.push({
            isActive: conditionMet,
            rule: "WEDNESDAY_THURSDAY",
            ruleDescription: "🔮 PREVIEW: Wednesday High < Monday High → Wednesday Low will be visited on Thursday",
            conditionMet,
            conditionDescription: conditionMet
              ? `✅ Wednesday's High (${wednesday.high.toFixed(2)}) < Monday's High (${monday.high.toFixed(2)})`
              : `❌ Wednesday's High (${wednesday.high.toFixed(2)}) ≥ Monday's High (${monday.high.toFixed(2)})`,
            targetPrice,
            targetHit: false,
            currentPrice,
            distanceToTarget,
            distancePercent,
            symbol,
            symbolName: name,
            referenceDay1: monday,
            referenceDay2: wednesday,
            predictionDay: "Thursday (tomorrow)",
            timestamp: now.toISOString(),
          });
        }
      }
    }

    return {
      success: true,
      predictions,
      currentDayOfWeek,
      currentDayName,
      lastUpdated: now.toISOString(),
    };
  } catch (error) {
    console.error("Error in Tom Hougaard analysis:", error);
    return {
      success: false,
      predictions: [],
      currentDayOfWeek: new Date().getDay(),
      currentDayName: DAY_NAMES[new Date().getDay()],
      lastUpdated: new Date().toISOString(),
      error: error instanceof Error ? error.message : "Unknown error",
    };
  }
}
