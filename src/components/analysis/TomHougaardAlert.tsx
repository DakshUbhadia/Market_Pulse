"use client";

/**
 * ═══════════════════════════════════════════════════════════════════════════
 *  TOM HOUGAARD ALERT BANNER
 * ═══════════════════════════════════════════════════════════════════════════
 * 
 * Displays Tom Hougaard's strategy predictions at the top of Market Scope page
 * 
 * Rules:
 * 1. Friday High < Thursday High → Friday Low visited on Monday
 * 2. Wednesday High < Monday High → Wednesday Low visited on Thursday
 * 
 * Backtest Results (1 year data):
 * - Overall accuracy: ~49% (target exactly hit)
 * - Within 1% of target: 78% of the time
 * - Best on NIFTY: 55-62% accuracy
 * ═══════════════════════════════════════════════════════════════════════════
 */

import { useEffect, useState, useCallback } from "react";
import { 
  AlertTriangle, 
  Target, 
  TrendingDown, 
  CheckCircle2, 
  Clock, 
  RefreshCw,
  ChevronDown,
  ChevronUp
} from "lucide-react";
import { 
  analyzeTomHougaardStrategy, 
  type TomHougaardAnalysis, 
  type TomHougaardPrediction 
} from "@/lib/actions/tom-hougaard.actions";
import type { MarketType } from "@/lib/constants";
import { cn } from "@/lib/utils";

interface TomHougaardAlertProps {
  readonly market: MarketType;
}

export default function TomHougaardAlert({ market }: TomHougaardAlertProps) {
  const [analysis, setAnalysis] = useState<TomHougaardAnalysis | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isExpanded, setIsExpanded] = useState(true);
  const [lastRefresh, setLastRefresh] = useState<Date>(new Date());

  const fetchAnalysis = useCallback(async () => {
    setIsLoading(true);
    try {
      const result = await analyzeTomHougaardStrategy(market);
      if (result?.predictions) {
        setAnalysis(result);
        // Cache the result in localStorage
        try {
          localStorage.setItem(`mp.tomHougaard.${market}`, JSON.stringify(result));
        } catch { /* ignore storage errors */ }
      }
      setLastRefresh(new Date());
    } catch (error) {
      console.error("Error fetching Tom Hougaard analysis:", error);
      // Load from cache on error
      try {
        const cached = localStorage.getItem(`mp.tomHougaard.${market}`);
        if (cached) setAnalysis(JSON.parse(cached) as TomHougaardAnalysis);
      } catch { /* ignore */ }
    } finally {
      setIsLoading(false);
    }
  }, [market]);

  useEffect(() => {
    // Load from cache immediately
    try {
      const cached = localStorage.getItem(`mp.tomHougaard.${market}`);
      if (cached) setAnalysis(JSON.parse(cached) as TomHougaardAnalysis);
    } catch { /* ignore */ }
    
    fetchAnalysis();
    
    // Refresh every 5 minutes (observation-only)
    const interval = setInterval(fetchAnalysis, 300000);
    return () => clearInterval(interval);
  }, [fetchAnalysis, market]);

  // Filter to only show active predictions (where condition is met)
  const activePredictions = analysis?.predictions.filter(p => p.conditionMet) || [];

  // Don't show anything if loading without cache, no analysis, or no active predictions
  if (isLoading && !analysis) {
    return null; // Don't show loading state
  }

  if (!analysis || activePredictions.length === 0) {
    return null; // Hide completely when no active signals
  }

  return (
    <div className="bg-linear-to-r from-amber-950/40 to-orange-950/40 border border-amber-500/40 rounded-lg overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between p-4 hover:bg-amber-900/20 transition-colors">
        <button
          type="button"
          className="flex-1 flex items-center gap-3 text-left"
          onClick={() => setIsExpanded(!isExpanded)}
          aria-expanded={isExpanded}
        >
          <div className="p-2 bg-amber-500/20 rounded-lg">
            <Target className="h-5 w-5 text-amber-400" />
          </div>
          <div>
            <h3 className="font-semibold text-amber-300 flex items-center gap-2">
              Tom Hougaard&apos;s Strategy
              {activePredictions.length > 0 && (
                <span className="px-2 py-0.5 bg-green-500/20 text-green-400 text-xs rounded-full">
                  {activePredictions.length} Active Signal{activePredictions.length > 1 ? "s" : ""}
                </span>
              )}
            </h3>
            <p className="text-xs text-muted-foreground">
              Day-to-day high/low relationship patterns • {analysis.currentDayName}
            </p>
          </div>
        </button>
        
        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={() => fetchAnalysis()}
            className="p-1.5 hover:bg-amber-500/20 rounded-lg transition-colors"
            title="Refresh"
          >
            <RefreshCw className={cn("h-4 w-4 text-amber-400", isLoading && "animate-spin")} />
          </button>
          <button
            type="button"
            onClick={() => setIsExpanded(!isExpanded)}
            className="p-1"
            aria-label={isExpanded ? "Collapse" : "Expand"}
          >
            {isExpanded ? (
              <ChevronUp className="h-5 w-5 text-muted-foreground" />
            ) : (
              <ChevronDown className="h-5 w-5 text-muted-foreground" />
            )}
          </button>
        </div>
      </div>

      {/* Content */}
      {isExpanded && (
        <div className="px-4 pb-4 space-y-3">
          {/* Backtest accuracy note */}
          {activePredictions.length > 0 && (
            <div className="bg-blue-500/10 border border-blue-500/20 rounded-lg p-2 text-xs text-blue-300">
              📊 <strong>Backtest (1 year):</strong> Target hit exactly ~50% of the time | Within 1% of target: 78% | NIFTY best performer: 55-62% accuracy
            </div>
          )}

          {/* Active Predictions - Green/Highlighted */}
          {activePredictions.map((prediction) => (
            <PredictionCard key={`${prediction.symbol}-${prediction.rule}-${prediction.predictionDay}`} prediction={prediction} isActive />
          ))}

          {/* Last Updated */}
          <div className="flex items-center justify-between text-xs text-muted-foreground pt-2 border-t border-amber-500/20">
            <span className="flex items-center gap-1">
              <Clock className="h-3 w-3" />
              Last updated: {lastRefresh.toLocaleTimeString()}
            </span>
            <span>Auto-refreshes every 5 minutes</span>
          </div>
        </div>
      )}
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════════════
//  PREDICTION CARD COMPONENT
// ═══════════════════════════════════════════════════════════════════════════

interface PredictionCardProps {
  readonly prediction: TomHougaardPrediction;
  readonly isActive: boolean;
}

function PredictionCard({ prediction, isActive }: PredictionCardProps) {
  const isPreview = prediction.ruleDescription.includes("PREVIEW");
  
  // Compute card styling based on state
  let cardClass = "bg-muted/30 border border-muted/40 opacity-60";
  let StatusIcon = <TrendingDown className="h-5 w-5 text-muted-foreground" />;
  
  if (isActive) {
    if (prediction.targetHit) {
      cardClass = "bg-green-500/30 border border-green-500/50";
      StatusIcon = <CheckCircle2 className="h-5 w-5 text-green-400" />;
    } else {
      cardClass = "bg-amber-500/20 border border-amber-500/40";
      StatusIcon = <AlertTriangle className="h-5 w-5 text-amber-400" />;
    }
  }
  
  return (
    <div className={cn("rounded-lg p-3 transition-all", cardClass)}>
      <div className="flex items-start justify-between gap-4">
        {/* Left: Symbol & Prediction */}
        <div className="flex-1 space-y-2">
          <div className="flex items-center gap-2">
            {StatusIcon}
            <span className="font-semibold text-foreground">
              {prediction.symbolName}
            </span>
            <span className="text-xs text-muted-foreground">
              ({prediction.symbol})
            </span>
            {isPreview && (
              <span className="px-1.5 py-0.5 bg-blue-500/20 text-blue-400 text-xs rounded">
                Preview
              </span>
            )}
          </div>

          <p className="text-sm text-muted-foreground">
            {prediction.ruleDescription}
          </p>

          <p className={cn(
            "text-sm",
            isActive ? "text-amber-300" : "text-muted-foreground"
          )}>
            {prediction.conditionDescription}
          </p>
        </div>

        {/* Right: Target & Status */}
        {isActive && (
          <div className="text-right space-y-1">
            <div className="text-xs text-muted-foreground">Target Price</div>
            <div className={cn(
              "text-lg font-bold",
              prediction.targetHit ? "text-green-400" : "text-amber-400"
            )}>
              ₹{prediction.targetPrice.toFixed(2)}
            </div>
            
            {prediction.targetHit ? (
              <div className="flex items-center gap-1 text-green-400 text-sm">
                <CheckCircle2 className="h-4 w-4" />
                TARGET HIT!
              </div>
            ) : (
              <div className="text-xs text-muted-foreground">
                <div>Current: ₹{prediction.currentPrice.toFixed(2)}</div>
                <div className={cn(
                  prediction.distancePercent < 0 ? "text-green-400" : "text-amber-400"
                )}>
                  {prediction.distancePercent > 0 ? "↓" : "↑"} {Math.abs(prediction.distancePercent).toFixed(2)}% to target
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Reference Data */}
      {isActive && (
        <div className="mt-3 pt-2 border-t border-amber-500/20 grid grid-cols-2 gap-4 text-xs">
          <div>
            <span className="text-muted-foreground">{prediction.referenceDay1.dayName} ({prediction.referenceDay1.date})</span>
            <div className="text-foreground">
              High: ₹{prediction.referenceDay1.high.toFixed(2)} | Low: ₹{prediction.referenceDay1.low.toFixed(2)}
            </div>
          </div>
          <div>
            <span className="text-muted-foreground">{prediction.referenceDay2.dayName} ({prediction.referenceDay2.date})</span>
            <div className="text-foreground">
              High: ₹{prediction.referenceDay2.high.toFixed(2)} | Low: ₹{prediction.referenceDay2.low.toFixed(2)}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
