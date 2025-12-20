"use client";
import React from "react";
import Image from "next/image";

const FeatureAlerts = () => {
  return (
    <section className="landing-section feature-section">
      <div className="landing-container">
        <div className="feature-content">
          {/* Left Side - Text Content */}
          <div className="feature-text">
            <h2>
              Never Miss a <span className="text-gold">Critical Move.</span>
            </h2>
            <p>
              Set custom price and volume alerts. Whether it&apos;s a breakout or a
              dip, we notify you the second it happens.
            </p>
            <ul className="feature-list">
              <li>
                <svg className="feature-list-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <polyline points="20 6 9 17 4 12" />
                </svg>
                <span>Real-time price threshold alerts</span>
              </li>
              <li>
                <svg className="feature-list-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <polyline points="20 6 9 17 4 12" />
                </svg>
                <span>Volume spike notifications</span>
              </li>
              <li>
                <svg className="feature-list-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <polyline points="20 6 9 17 4 12" />
                </svg>
                <span>Email, SMS, and push notifications</span>
              </li>
              <li>
                <svg className="feature-list-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <polyline points="20 6 9 17 4 12" />
                </svg>
                <span>Unlimited alerts on all plans</span>
              </li>
            </ul>
          </div>

          {/* Right Side - Alert Preview */}
          <div className="feature-visual">
            <div className="feature-image glow-green">
              <Image
                src="/assets/images/Alert.png"
                alt="Price Alert Modal - Set custom price and volume alerts"
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

export default FeatureAlerts;
