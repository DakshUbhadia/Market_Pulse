"use client";
import TradingViewWidget from "@/components/ui/TradingViewWidgets";
import {
  BSE_MARKET_DATA,
  CRYPTO_MARKETS,
  MARKET_DATA,
  MARKET_HEATMAP,
  MARKET_OVERVIEW_CHART,
  NEWS_WIDGET,
  TICKER_TAPE,
  USA_MARKET_DATA,
} from "@/lib/constants";

const Home = () => {
  // TradingView Advanced Chart embed script URL
  const marketOverviewScriptURL =
    "https://s3.tradingview.com/external-embedding/embed-widget-market-overview.js";
  const tickerTapeScriptURL =
    "https://s3.tradingview.com/external-embedding/embed-widget-ticker-tape.js";
  const stockHeatmapScriptURL =
    "https://s3.tradingview.com/external-embedding/embed-widget-stock-heatmap.js";
  const newsScriptURL =
    "https://s3.tradingview.com/external-embedding/embed-widget-timeline.js";
  const marketDataScriptURL =
    "https://s3.tradingview.com/external-embedding/embed-widget-market-quotes.js";
  const cryptoMarketsScriptURL =
    "https://s3.tradingview.com/external-embedding/embed-widget-screener.js";

  const marketOverviewConfig = { ...MARKET_OVERVIEW_CHART, width: "100%", height: 600 };
  const heatmapConfig = { ...MARKET_HEATMAP, width: "100%", height: 600 };

  return (
    <main className="flex flex-col gap-8">
      <section>
        <TradingViewWidget scriptURL={tickerTapeScriptURL} config={TICKER_TAPE} height={46} />
      </section>

      <section className="flex flex-col lg:flex-row gap-8 w-full">
        <div className="w-full lg:w-[400px] rounded-lg border border-border bg-card p-4">
          <div className="mb-4 flex items-center gap-3">
            <div className="h-6 w-1.5 rounded-full bg-yellow-500" />
            <h2 className="text-xl font-semibold text-foreground">Market Overview</h2>
          </div>
          <TradingViewWidget scriptURL={marketOverviewScriptURL} config={marketOverviewConfig} height={600} />
        </div>
        <div className="w-full lg:flex-1 rounded-lg border border-border bg-card p-4">
          <div className="mb-4 flex items-center gap-3">
            <div className="h-6 w-1.5 rounded-full bg-yellow-500" />
            <h2 className="text-xl font-semibold text-foreground">Stock Heatmap</h2>
          </div>
          <TradingViewWidget scriptURL={stockHeatmapScriptURL} config={heatmapConfig} height={600} />
        </div>
      </section>

      <section className="flex flex-col lg:flex-row gap-8 w-full">
        <div className="w-full lg:flex-1 rounded-lg border border-border bg-card p-4">
          <div className="mb-4 flex items-center gap-3">
            <div className="h-6 w-1.5 rounded-full bg-yellow-500" />
            <h2 className="text-xl font-semibold text-foreground">Sector-wise Overview</h2>
          </div>
          <TradingViewWidget scriptURL={marketDataScriptURL} config={MARKET_DATA} height={600} />
        </div>
        <div className="w-full lg:w-[463px] rounded-lg border border-border bg-card p-4">
          <div className="mb-4 flex items-center gap-3">
            <div className="h-6 w-1.5 rounded-full bg-yellow-500" />
            <h2 className="text-xl font-semibold text-foreground">Crypto Markets</h2>
          </div>
          <TradingViewWidget scriptURL={cryptoMarketsScriptURL} config={CRYPTO_MARKETS} height={600} />
        </div>
        <div className="w-full lg:w-[400px] rounded-lg border border-border bg-card p-4">
          <div className="mb-4 flex items-center gap-3">
            <div className="h-6 w-1.5 rounded-full bg-yellow-500" />
            <h2 className="text-xl font-semibold text-foreground">News</h2>
          </div>
          <TradingViewWidget scriptURL={newsScriptURL} config={NEWS_WIDGET} height={600} />
        </div>
      </section>

      <section className="w-full rounded-lg border border-border bg-card p-4">
        <div className="mb-4 flex items-center gap-3">
          <div className="h-6 w-1.5 rounded-full bg-yellow-500" />
          <h2 className="text-xl font-semibold text-foreground">USA Market Detailed Insights</h2>
        </div>
        <TradingViewWidget scriptURL={cryptoMarketsScriptURL} config={USA_MARKET_DATA} height={550} />
      </section>

      <section className="w-full rounded-lg border border-border bg-card p-4">
        <div className="mb-4 flex items-center gap-3">
          <div className="h-6 w-1.5 rounded-full bg-yellow-500" />
          <h2 className="text-xl font-semibold text-foreground">BSE Market Detailed Insights</h2>
        </div>
        <TradingViewWidget scriptURL={cryptoMarketsScriptURL} config={BSE_MARKET_DATA} height={550} />
      </section>
    </main>
  );
};

export default Home;