"use client";

import { useParams } from "next/navigation";
import { Star } from "lucide-react";
import TradingViewWidget from "@/components/ui/TradingViewWidgets";
import { useWatchlist } from "@/context/WatchlistContext";
import {
  ADVANCED_CHART_1,
  ADVANCED_CHART_2,
  COMPANY_PROFILE,
  FUNDAMENTAL_DATA,
  STOCK_SYMBOL,
  TECHNICAL_ANALYSIS,
  toTradingViewSymbol,
} from "@/lib/constants";

const SYMBOL_SCRIPT_URL =
  "https://s3.tradingview.com/external-embedding/embed-widget-symbol-info.js";
const TECHNICAL_ANALYSIS_SCRIPT_URL =
  "https://s3.tradingview.com/external-embedding/embed-widget-technical-analysis.js";
const FUNDAMENTAL_DATA_SCRIPT_URL =
  "https://s3.tradingview.com/external-embedding/embed-widget-financials.js";
const COMPANY_PROFILE_SCRIPT_URL =
  "https://s3.tradingview.com/external-embedding/embed-widget-symbol-profile.js";
const ADVANCED_CHART_SCRIPT_URL =
  "https://s3.tradingview.com/external-embedding/embed-widget-advanced-chart.js";

export default function StockDetailPage() {
  const params = useParams();
  const rawSymbol = typeof params.symbol === "string" ? params.symbol : "";
  const symbol = decodeURIComponent(rawSymbol);
  const { isInWatchlist, toggleWatchlist } = useWatchlist();

  const tvSymbol = toTradingViewSymbol(symbol);
  const config = {
    symbolInfo: STOCK_SYMBOL(tvSymbol),
    technicalAnalysis: TECHNICAL_ANALYSIS(tvSymbol),
    fundamentalData: FUNDAMENTAL_DATA(tvSymbol),
    companyProfile: COMPANY_PROFILE(tvSymbol),
    advancedChart1: ADVANCED_CHART_1(tvSymbol),
    advancedChart2: ADVANCED_CHART_2(tvSymbol),
  };

  // Extract display name from symbol (e.g., "NASDAQ:AAPL" -> "AAPL")
  const displaySymbol = symbol.includes(":") ? symbol.split(":")[1] : symbol;
  const exchange = symbol.includes(":") ? symbol.split(":")[0] : "US";
  const inWatchlist = isInWatchlist(displaySymbol);

  const handleToggleWatchlist = () => {
    toggleWatchlist({
      symbol: displaySymbol,
      name: displaySymbol, // Will be updated with real name from API
      exchange: exchange,
    });
  };

  return (
    <main className="grid grid-cols-1 gap-8 pb-10 lg:grid-cols-[minmax(0,1fr)_420px] lg:items-start">
      <section className="flex min-w-0 flex-col gap-8">
        <div className="rounded-xl border border-border bg-card p-5">
          <div className="mb-4 flex items-center gap-3">
            <div className="h-6 w-1.5 rounded-full bg-yellow-500" />
            <div className="min-w-0">
              <h1 className="truncate text-xl font-semibold text-foreground">{displaySymbol}</h1>
              <p className="text-sm text-muted-foreground">{exchange} • Live overview</p>
            </div>
          </div>

          <div className="overflow-hidden rounded-lg border border-border/60 bg-background/40">
            <TradingViewWidget scriptURL={SYMBOL_SCRIPT_URL} config={config.symbolInfo} height={220} />
          </div>
        </div>

        <div className="rounded-xl border border-border bg-card p-5">
          <div className="mb-4 flex items-center gap-3">
            <div className="h-6 w-1.5 rounded-full bg-yellow-500" />
            <h2 className="text-xl font-semibold text-foreground">Advanced Chart</h2>
          </div>
          <div className="overflow-hidden rounded-lg border border-border/60 bg-background/40">
            <TradingViewWidget scriptURL={ADVANCED_CHART_SCRIPT_URL} config={config.advancedChart1} height={700} />
          </div>
        </div>

        <div className="rounded-xl border border-border bg-card p-5">
          <div className="mb-4 flex items-center gap-3">
            <div className="h-6 w-1.5 rounded-full bg-yellow-500" />
            <h2 className="text-xl font-semibold text-foreground">Compare & Context</h2>
          </div>
          <div className="overflow-hidden rounded-lg border border-border/60 bg-background/40">
            <TradingViewWidget scriptURL={ADVANCED_CHART_SCRIPT_URL} config={config.advancedChart2} height={640} />
          </div>
        </div>
      </section>

      <aside className="flex w-full flex-col gap-8 lg:w-[420px] lg:justify-self-end">
        <div className="rounded-xl border border-border bg-card p-5">
          <div className="mb-4 flex items-center gap-3">
            <div className="h-6 w-1.5 rounded-full bg-yellow-500" />
            <h2 className="text-xl font-semibold text-foreground">Watchlist</h2>
          </div>
          <button
            type="button"
            onClick={handleToggleWatchlist}
            className={`
              group flex w-full items-center justify-center gap-2 rounded-md px-6 py-3 text-sm font-semibold
              transition-all duration-300
              ${
                inWatchlist
                  ? "border border-yellow-500 bg-yellow-500/20 text-yellow-500 hover:bg-yellow-500/30"
                  : "border border-yellow-500/50 bg-linear-to-r from-yellow-600 to-yellow-500 text-black hover:from-yellow-500 hover:to-yellow-400 hover:shadow-lg hover:shadow-yellow-500/25"
              }
            `}
          >
            <Star
              className={`h-5 w-5 transition-transform group-hover:scale-110 ${
                inWatchlist ? "fill-yellow-500" : ""
              }`}
            />
            <span>{inWatchlist ? "In Watchlist" : "Add to Watchlist"}</span>
          </button>
        </div>

        <div className="rounded-xl border border-border bg-card p-5">
          <div className="mb-4 flex items-center gap-3">
            <div className="h-6 w-1.5 rounded-full bg-yellow-500" />
            <h2 className="text-xl font-semibold text-foreground">Company Profile</h2>
          </div>
          <div className="overflow-hidden rounded-lg border border-border/60 bg-background/40">
            <TradingViewWidget scriptURL={COMPANY_PROFILE_SCRIPT_URL} config={config.companyProfile} height={520} />
          </div>
        </div>

        <div className="rounded-xl border border-border bg-card p-5">
          <div className="mb-4 flex items-center gap-3">
            <div className="h-6 w-1.5 rounded-full bg-yellow-500" />
            <h2 className="text-xl font-semibold text-foreground">Fundamentals</h2>
          </div>
          <div className="overflow-hidden rounded-lg border border-border/60 bg-background/40">
            <TradingViewWidget scriptURL={FUNDAMENTAL_DATA_SCRIPT_URL} config={config.fundamentalData} height={520} />
          </div>
        </div>

        <div className="rounded-xl border border-border bg-card p-5">
          <div className="mb-4 flex items-center gap-3">
            <div className="h-6 w-1.5 rounded-full bg-yellow-500" />
            <h2 className="text-xl font-semibold text-foreground">Technical Analysis</h2>
          </div>
          <div className="overflow-hidden rounded-lg border border-border/60 bg-background/40">
            <TradingViewWidget scriptURL={TECHNICAL_ANALYSIS_SCRIPT_URL} config={config.technicalAnalysis} height={460} />
          </div>
        </div>
      </aside>
    </main>
  );
}
