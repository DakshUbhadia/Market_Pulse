"use client";
import React from "react";

const LandingFooter = () => {
  return (
    <footer className="landing-footer">
      <div className="landing-container">
        <div className="footer-content">
          {/* Brand */}
          <div className="footer-brand">
            <h3>
              Market<span className="text-gold">Pulse</span>
            </h3>
            <p>
              Empowering traders with real-time market intelligence, advanced
              analytics, and professional-grade tools.
            </p>
          </div>
        </div>

        <div className="footer-bottom">
          <p>© {new Date().getFullYear()} Market Pulse. All rights reserved.</p>
        </div>
      </div>
    </footer>
  );
};

export default LandingFooter;
