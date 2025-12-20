"use client";
import React from "react";
import Image from "next/image";

const MarketSnapshotSection = () => {
  const stocks = [
    { symbol: "AAPL", name: "Apple Inc.", price: "$178.72", change: "+2.34%", isUp: true },
    { symbol: "NVDA", name: "NVIDIA Corp.", price: "$875.38", change: "+5.67%", isUp: true },
    { symbol: "TSLA", name: "Tesla Inc.", price: "$248.50", change: "-1.23%", isUp: false },
    { symbol: "MSFT", name: "Microsoft Corp.", price: "$378.91", change: "+1.45%", isUp: true },
  ];

  return (
    <section className="landing-section snapshot-section">
      <div className="landing-container">
        <div className="section-header">
          <h2>
            Spot Opportunities <span className="text-gold">Instantly.</span>
          </h2>
          <p>
            Don&apos;t guess. See what&apos;s moving with our live Sector Heatmaps and
            Top Gainer lists.
          </p>
        </div>

        {/* Stock Cards Grid */}
        <div className="snapshot-grid">
          {stocks.map((stock) => (
            <div key={stock.symbol} className="glass-card stock-card">
              <div className="stock-logo">{stock.symbol.slice(0, 2)}</div>
              <div className="stock-info">
                <div className="stock-name">{stock.name}</div>
                <div className="stock-symbol">{stock.symbol}</div>
              </div>
              <div className="stock-price">
                <div className="stock-value">{stock.price}</div>
                <div className={`stock-change ${stock.isUp ? "up" : "down"}`}>
                  {stock.change}
                </div>
              </div>
            </div>
          ))}
        </div>

        {/* Heatmap Image */}
        <div className="mini-heatmap-container" style={{ marginTop: "40px", position: "relative" }}>
          <Image
            src="/assets/images/heatmap.png"
            alt="Market Sector Heatmap"
            width={1000}
            height={500}
            className="feature-screenshot"
            style={{ width: "100%", height: "auto" }}
          />
        </div>
      </div>
    </section>
  );
};

export default MarketSnapshotSection;
