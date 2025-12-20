"use client";
import React from "react";
import Image from "next/image";

const WatchlistSection = () => {
  return (
    <section className="landing-section watchlist-section">
      <div className="landing-container">
        <div className="section-header center">
          <h2>
            Your Personal <span className="text-gold">Command Center.</span>
          </h2>
          <p>
            Track your favorite stocks, manage alerts, and stay ahead of the market—all in one place.
          </p>
        </div>

        {/* 3D Tilted Screenshot with Gold Glow */}
        <div className="watchlist-showcase">
          {/* Gold Glow Backdrop */}
          <div className="gold-glow-backdrop"></div>
          
          {/* 3D Tilted Image Container */}
          <div className="watchlist-image-container">
            <Image
              src="/assets/images/watchlist-alerts.png"
              alt="Watchlist & Alerts Interface - Track stocks and manage alerts"
              width={900}
              height={550}
              className="watchlist-screenshot"
              priority
            />
          </div>
        </div>

        {/* Feature Pills */}
        <div className="watchlist-features">
          <div className="feature-pill">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83" />
            </svg>
            <span>Real-time Updates</span>
          </div>
          <div className="feature-pill">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9" />
              <path d="M13.73 21a2 2 0 0 1-3.46 0" />
            </svg>
            <span>Smart Alerts</span>
          </div>
          <div className="feature-pill">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M3 3v18h18" />
              <path d="M18.7 8l-5.1 5.2-2.8-2.7L7 14.3" />
            </svg>
            <span>Performance Tracking</span>
          </div>
          <div className="feature-pill">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="11" cy="11" r="8" />
              <path d="m21 21-4.35-4.35" />
            </svg>
            <span>Quick Search</span>
          </div>
        </div>
      </div>
    </section>
  );
};

export default WatchlistSection;
