"use client";
import React from "react";

const PortfolioSection = () => {
  return (
    <section className="landing-section portfolio-section">
      <div className="landing-container">
        <div className="section-header">
          <h2>
            Visualize Your <span className="text-gold">Financial Growth.</span>
          </h2>
          <p>
            Keep a pulse on your net worth. Monitor your watchlist and holdings
            in a unified, professional dashboard.
          </p>
        </div>

        {/* Portfolio Chart Card */}
        <div className="portfolio-chart">
          <div className="chart-header">
            <div className="chart-title">
              <h3>Portfolio Value</h3>
              <span>Last 30 Days</span>
            </div>
            <div className="chart-value">
              <div className="chart-amount">$127,845.32</div>
              <div className="chart-change">+$12,540.00 (+10.9%)</div>
            </div>
          </div>

          <div className="chart-visual">
            <svg className="chart-svg" viewBox="0 0 800 250" preserveAspectRatio="none">
              <defs>
                <linearGradient id="goldGradient" x1="0%" y1="0%" x2="0%" y2="100%">
                  <stop offset="0%" stopColor="#D4AF37" stopOpacity="0.4" />
                  <stop offset="100%" stopColor="#D4AF37" stopOpacity="0" />
                </linearGradient>
              </defs>
              
              {/* Grid Lines */}
              <g className="chart-grid">
                <line x1="0" y1="50" x2="800" y2="50" />
                <line x1="0" y1="100" x2="800" y2="100" />
                <line x1="0" y1="150" x2="800" y2="150" />
                <line x1="0" y1="200" x2="800" y2="200" />
              </g>
              
              {/* Area Fill */}
              <path
                className="chart-area"
                d="M0 200 Q80 180 160 170 T320 140 T480 100 T640 80 T800 40 L800 250 L0 250 Z"
              />
              
              {/* Line */}
              <path
                className="chart-line"
                d="M0 200 Q80 180 160 170 T320 140 T480 100 T640 80 T800 40"
              />
              
              {/* Data Points */}
              <circle cx="0" cy="200" r="4" fill="#D4AF37" />
              <circle cx="160" cy="170" r="4" fill="#D4AF37" />
              <circle cx="320" cy="140" r="4" fill="#D4AF37" />
              <circle cx="480" cy="100" r="4" fill="#D4AF37" />
              <circle cx="640" cy="80" r="4" fill="#D4AF37" />
              <circle cx="800" cy="40" r="6" fill="#D4AF37" style={{ filter: "drop-shadow(0 0 8px rgba(212, 175, 55, 0.8))" }} />
            </svg>
          </div>

          {/* Portfolio Holdings Mini List */}
          <div style={{ 
            marginTop: "30px", 
            display: "grid", 
            gridTemplateColumns: "repeat(auto-fit, minmax(150px, 1fr))", 
            gap: "16px",
            paddingTop: "20px",
            borderTop: "1px solid rgba(255, 255, 255, 0.05)"
          }}>
            {[
              { symbol: "AAPL", shares: "50", value: "$8,936", change: "+4.2%" },
              { symbol: "NVDA", shares: "25", value: "$21,884", change: "+12.3%" },
              { symbol: "MSFT", shares: "30", value: "$11,367", change: "+2.1%" },
              { symbol: "GOOGL", shares: "15", value: "$2,142", change: "-0.8%" },
            ].map((holding) => (
              <div 
                key={holding.symbol}
                style={{ 
                  background: "rgba(255, 255, 255, 0.03)",
                  padding: "16px",
                  borderRadius: "12px",
                  textAlign: "left"
                }}
              >
                <div style={{ color: "#D4AF37", fontWeight: 600, marginBottom: "4px" }}>
                  {holding.symbol}
                </div>
                <div style={{ fontSize: "0.85rem", color: "#737373", marginBottom: "8px" }}>
                  {holding.shares} shares
                </div>
                <div style={{ color: "#fff", fontWeight: 600 }}>{holding.value}</div>
                <div style={{ 
                  fontSize: "0.85rem", 
                  color: holding.change.startsWith("+") ? "#10b981" : "#ef4444" 
                }}>
                  {holding.change}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
};

export default PortfolioSection;
