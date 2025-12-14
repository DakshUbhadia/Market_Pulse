"use client";
import TradingViewWidget from "@/components/ui/TradingViewWidgets";
import { MARKET_OVERVIEW_CHART, TICKER_TAPE, MARKET_HEATMAP, NEWS_WIDGET, MARKET_DATA, CRYPTO_MARKETS } from "@/lib/constants";

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

  return (
    <main className="flex flex-col gap-4">
      <div className="w-full">
        <TradingViewWidget
          title="Ticker Tape"
          scriptURL={tickerTapeScriptURL}
          config={TICKER_TAPE}
          height={46}
        />
      </div>
      <div className="flex flex-col lg:flex-row gap-4 w-full">
        <div className="w-full lg:w-[400px]">
          <TradingViewWidget
            title="Market Overview"
            scriptURL={marketOverviewScriptURL}
            config={MARKET_OVERVIEW_CHART}
            height={600}
          />
        </div>
        <div className="w-full lg:flex-1">
          <TradingViewWidget
            title="Stock Heatmap"
            scriptURL={stockHeatmapScriptURL}
            config={MARKET_HEATMAP}
            height={600}
          />
        </div>
      </div>
      <div className="flex flex-col lg:flex-row gap-4 w-full">
        <div className="w-full lg:flex-1">
          <TradingViewWidget
            title="Market Data"
            scriptURL={marketDataScriptURL}
            config={MARKET_DATA}
            height={600}
          />
        </div>
        <div className="w-full lg:w-[463px]">
          <TradingViewWidget
            title="Crypto Markets"
            scriptURL={cryptoMarketsScriptURL}
            config={CRYPTO_MARKETS}
            height={600}
          />
        </div>
        <div className="w-full lg:w-[400px]">
          <TradingViewWidget
            title="News"
            scriptURL={newsScriptURL}
            config={NEWS_WIDGET}
            height={600}
          />
        </div>
      </div>
    </main>
  );
};

export default Home;