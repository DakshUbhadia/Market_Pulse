"use client";
import React from "react";
import Image from "next/image";

const FeatureAnalysis = () => {
  return (
    <section className="landing-section feature-section">
      <div className="landing-container">
        <div className="feature-content">
          {/* Left Side - Text Content */}
          <div className="feature-text">
            <h2>
              Technical Analysis <span className="text-gold">Made Simple.</span>
            </h2>
            <p>
              From RSI to Moving Averages, get automated technical ratings for
              every stock. Know when to buy and when to sell.
            </p>
            <ul className="feature-list">
              <li>
                <svg className="feature-list-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <polyline points="20 6 9 17 4 12" />
                </svg>
                <span>12+ technical indicators analyzed</span>
              </li>
              <li>
                <svg className="feature-list-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <polyline points="20 6 9 17 4 12" />
                </svg>
                <span>Instant Buy/Sell/Hold ratings</span>
              </li>
              <li>
                <svg className="feature-list-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <polyline points="20 6 9 17 4 12" />
                </svg>
                <span>Historical accuracy tracking</span>
              </li>
              <li>
                <svg className="feature-list-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <polyline points="20 6 9 17 4 12" />
                </svg>
                <span>Custom timeframe analysis</span>
              </li>
            </ul>
          </div>

          {/* Right Side - Technical Analysis Screenshot */}
          <div className="feature-visual">
            <div className="feature-image">
              <Image
                src="/assets/images/technical-analysis.png"
                alt="Technical Analysis Gauge - Buy/Sell/Hold ratings"
                width={450}
                height={350}
                className="feature-screenshot"
              />
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};

export default FeatureAnalysis;
