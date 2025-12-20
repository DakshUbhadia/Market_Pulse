"use client";
import React from "react";
import Link from "next/link";

const CTASection = () => {
  return (
    <section className="landing-section cta-section">
      {/* Decorative Rings */}
      <div className="cta-ring"></div>
      <div className="cta-ring"></div>
      
      <div className="landing-container">
        <div className="cta-content">
          <h2>
            Ready to <span className="text-gold">Master the Market?</span>
          </h2>
          <p>
            Join thousands of traders who trust Market Pulse for real-time
            insights, powerful analytics, and smarter trading decisions.
          </p>
          <div className="cta-buttons">
            <Link href="/sign-up" className="btn-gold">
              Get Started Free
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
              Sign In to Dashboard
            </Link>
          </div>
        </div>
      </div>
    </section>
  );
};

export default CTASection;
