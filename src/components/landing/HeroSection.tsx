"use client";
import React from "react";
import Link from "next/link";
import Image from "next/image";

const HeroSection = () => {
  return (
    <section className="hero-section">
      <div className="landing-container">
        <div className="hero-content">
          {/* Left Side - Text Content */}
          <div className="hero-text">
            <h1>
              Master the Market with{" "}
              <span className="text-gold">Real-Time Precision.</span>
            </h1>
            <p>
              Get the inside scoop on global markets. Advanced heatmaps, instant
              signals, and smart alerts—all in one magnificent dashboard.
            </p>
            <div className="hero-cta">
              <Link href="/sign-up" className="btn-gold">
                Start Trading Free
                <svg
                  width="20"
                  height="20"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                >
                  <path d="M5 12h14M12 5l7 7-7 7" />
                </svg>
              </Link>
              <Link href="/sign-in" className="btn-gold-outline">
                Sign In
              </Link>
            </div>

            {/* Stats */}
            <div className="hero-stats">
              <div className="hero-stat">
                <div className="hero-stat-value">$2.4T+</div>
                <div className="hero-stat-label">Daily Volume Tracked</div>
              </div>
              <div className="hero-stat">
                <div className="hero-stat-value">150+</div>
                <div className="hero-stat-label">Global Markets</div>
              </div>
              <div className="hero-stat">
                <div className="hero-stat-value">50K+</div>
                <div className="hero-stat-label">Active Traders</div>
              </div>
            </div>
          </div>

          {/* Right Side - Dashboard Screenshot */}
          <div className="hero-visual">
            <div className="dashboard-mockup">
              <Image
                src="/assets/images/dashboard.png"
                alt="Market Pulse Dashboard - Real-time stock market visualization"
                width={600}
                height={400}
                className="dashboard-img"
                priority
              />
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};

export default HeroSection;
