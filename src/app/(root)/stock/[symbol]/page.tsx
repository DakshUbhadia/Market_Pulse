"use client";

import { useParams, notFound } from "next/navigation";
import { Star } from "lucide-react";
import { useState } from "react";
import TradingViewWidget from "@/components/ui/TradingViewWidgets";
import {
  STOCK_SYMBOL_APPL,
  TECHNICAL_ANALYSIS_APPL,
  FUNDAMENTAL_DATA_APPL,
  COMPANY_PROFILE_APPL,
  ADVANCED_CHART_1_APPL,
  ADVANCED_CHART_2_APPL,
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

type SupportedSymbol = "AAPL";

const STOCK_CONFIGS: Record<
  SupportedSymbol,
  {
    name: string;
    symbolInfo: typeof STOCK_SYMBOL_APPL;
    technicalAnalysis: typeof TECHNICAL_ANALYSIS_APPL;
    fundamentalData: typeof FUNDAMENTAL_DATA_APPL;
    companyProfile: typeof COMPANY_PROFILE_APPL;
    advancedChart1: typeof ADVANCED_CHART_1_APPL;
    advancedChart2: typeof ADVANCED_CHART_2_APPL;
  }
> = {
  AAPL: {
    name: "Apple Inc.",
    symbolInfo: STOCK_SYMBOL_APPL,
    technicalAnalysis: TECHNICAL_ANALYSIS_APPL,
    fundamentalData: FUNDAMENTAL_DATA_APPL,
    companyProfile: COMPANY_PROFILE_APPL,
    advancedChart1: ADVANCED_CHART_1_APPL,
    advancedChart2: ADVANCED_CHART_2_APPL,
  },
};

export default function StockDetailPage() {
  const params = useParams();
  const symbol = (params.symbol as string)?.toUpperCase() as SupportedSymbol;
  const [isInWatchlist, setIsInWatchlist] = useState(false);

  const config = STOCK_CONFIGS[symbol];

  if (!config) {
    notFound();
  }

  const handleToggleWatchlist = () => {
    setIsInWatchlist((prev) => {
      const next = !prev;
      console.log("watchlist", symbol, next);
      return next;
    });
  };

  return (
    <main className="grid grid-cols-1 gap-6 pb-10 lg:grid-cols-[minmax(0,1fr)_420px] lg:items-start">
      <section className="flex min-w-0 flex-col gap-6">
        <div className="overflow-hidden rounded-md border bg-[#0F0F0F]">
          <TradingViewWidget
            scriptURL={SYMBOL_SCRIPT_URL}
            config={config.symbolInfo}
            height={140}
          />
        </div>

        <div className="overflow-hidden rounded-md border bg-[#0F0F0F]">
          <TradingViewWidget
            scriptURL={ADVANCED_CHART_SCRIPT_URL}
            config={config.advancedChart1}
            height={560}
          />
        </div>

        <div className="overflow-hidden rounded-md border bg-[#0F0F0F]">
          <TradingViewWidget
            scriptURL={ADVANCED_CHART_SCRIPT_URL}
            config={config.advancedChart2}
            height={360}
          />
        </div>
      </section>

      <aside className="flex w-full flex-col gap-6 lg:w-[420px] lg:justify-self-end">
        <button
          type="button"
          onClick={handleToggleWatchlist}
          className={`
            group flex w-full items-center justify-center gap-2 rounded-md px-6 py-3 text-sm font-semibold
            transition-all duration-300
            ${
              isInWatchlist
                ? "border border-yellow-500 bg-yellow-500/20 text-yellow-500 hover:bg-yellow-500/30"
                : "border border-yellow-500/50 bg-linear-to-r from-yellow-600 to-yellow-500 text-black hover:from-yellow-500 hover:to-yellow-400 hover:shadow-lg hover:shadow-yellow-500/25"
            }
          `}
        >
          <Star
            className={`h-5 w-5 transition-transform group-hover:scale-110 ${
              isInWatchlist ? "fill-yellow-500" : ""
            }`}
          />
          <span>{isInWatchlist ? "In Watchlist" : "Add to Watchlist"}</span>
        </button>

        <div className="">
          <TradingViewWidget
            scriptURL={TECHNICAL_ANALYSIS_SCRIPT_URL}
            config={config.technicalAnalysis}
            height={460}
          />
        </div>

        <div className="">
          <TradingViewWidget
            scriptURL={COMPANY_PROFILE_SCRIPT_URL}
            config={config.companyProfile}
            height={520}
          />
        </div>

        <div className="">
          <TradingViewWidget
            scriptURL={FUNDAMENTAL_DATA_SCRIPT_URL}
            config={config.fundamentalData}
            height={520}
          />
        </div>
      </aside>
    </main>
  );
}
