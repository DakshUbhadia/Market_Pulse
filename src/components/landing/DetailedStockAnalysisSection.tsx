"use client";
import React from "react";
import Image from "next/image";

const DetailedStockAnalysisSection = () => {
  return (
    <section className="landing-section feature-section">
      <div className="landing-container">
        <div className="feature-content">
          {/* Left Side - Screenshot */}
          <div className="feature-visual">
            <div className="feature-image">
              <Image
                src="/assets/images/stock-detailed-analysis.png"
                alt="Detailed Stock Analysis - Advanced charts, fundamentals, and technical insights"
                width={450}
                height={350}
                className="feature-screenshot"
                priority
              />
            </div>
          </div>

          {/* Right Side - Text Content */}
          <div className="feature-text">
            <h2>
              Detailed Stock <span className="text-gold">Analysis.</span>
            </h2>
            <p>
              Open any stock to get a full breakdown—advanced charts, fundamentals, company profile,
              and technical analysis in one clean view. Add it to your watchlist in one click.
            </p>
            <ul className="feature-list">
              <li>
                <svg className="feature-list-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <polyline points="20 6 9 17 4 12" />
                </svg>
                <span>Advanced interactive charts and comparisons</span>
              </li>
              <li>
                <svg className="feature-list-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <polyline points="20 6 9 17 4 12" />
                </svg>
                <span>Company profile, fundamentals, and key metrics</span>
              </li>
              <li>
                <svg className="feature-list-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <polyline points="20 6 9 17 4 12" />
                </svg>
                <span>Technical rating panels for quick decision support</span>
              </li>
              <li>
                <svg className="feature-list-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <polyline points="20 6 9 17 4 12" />
                </svg>
                <span>One-click watchlist add/remove</span>
              </li>
            </ul>
          </div>
        </div>
      </div>
    </section>
  );
};

export default DetailedStockAnalysisSection;
