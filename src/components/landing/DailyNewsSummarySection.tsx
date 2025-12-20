"use client";
import React from "react";
import Image from "next/image";

const DailyNewsSummarySection = () => {
  return (
    <section className="landing-section feature-section">
      <div className="landing-container">
        <div className="feature-content">
          {/* Left Side - Screenshot */}
          <div className="feature-visual">
            <div className="feature-image">
              <Image
                src="/assets/images/daily-news-summary.png"
                alt="Daily News Summary - Personalized market brief and watchlist news"
                width={450}
                height={350}
                className="feature-screenshot"
              />
            </div>
          </div>

          {/* Right Side - Text Content */}
          <div className="feature-text">
            <h2>
              Daily News <span className="text-gold">Summary.</span>
            </h2>
            <p>
              Start every day with a clean, AI-powered market brief delivered to your inbox—plus top
              headlines for the stocks you actually track in your watchlist.
            </p>
            <ul className="feature-list">
              <li>
                <svg className="feature-list-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <polyline points="20 6 9 17 4 12" />
                </svg>
                <span>Daily market recap with key themes</span>
              </li>
              <li>
                <svg className="feature-list-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <polyline points="20 6 9 17 4 12" />
                </svg>
                <span>Watchlist stock news included automatically</span>
              </li>
              <li>
                <svg className="feature-list-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <polyline points="20 6 9 17 4 12" />
                </svg>
                <span>Delivered by email—no noise, just signal</span>
              </li>
              <li>
                <svg className="feature-list-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <polyline points="20 6 9 17 4 12" />
                </svg>
                <span>Control subscriptions anytime in Settings</span>
              </li>
            </ul>
          </div>
        </div>
      </div>
    </section>
  );
};

export default DailyNewsSummarySection;
