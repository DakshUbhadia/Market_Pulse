"use client";
import React, { useMemo } from "react";
import { useRouter, usePathname } from "next/navigation";
import Image from "next/image";
import "./auth.css";

// Pre-generated candle data to avoid impure function calls during render
const CANDLE_DATA = [
  { id: 0, isGreen: true, left: "5%", delay: "0s", duration: "14s", height: "55px" },
  { id: 1, isGreen: false, left: "12%", delay: "2s", duration: "16s", height: "70px" },
  { id: 2, isGreen: true, left: "18%", delay: "1s", duration: "13s", height: "45px" },
  { id: 3, isGreen: true, left: "25%", delay: "4s", duration: "18s", height: "65px" },
  { id: 4, isGreen: false, left: "32%", delay: "3s", duration: "15s", height: "50px" },
  { id: 5, isGreen: true, left: "38%", delay: "6s", duration: "17s", height: "75px" },
  { id: 6, isGreen: false, left: "45%", delay: "1.5s", duration: "14s", height: "60px" },
  { id: 7, isGreen: true, left: "52%", delay: "5s", duration: "19s", height: "48px" },
  { id: 8, isGreen: true, left: "58%", delay: "2.5s", duration: "16s", height: "72px" },
  { id: 9, isGreen: false, left: "65%", delay: "4.5s", duration: "13s", height: "55px" },
  { id: 10, isGreen: true, left: "72%", delay: "0.5s", duration: "18s", height: "68px" },
  { id: 11, isGreen: false, left: "78%", delay: "7s", duration: "15s", height: "42px" },
  { id: 12, isGreen: true, left: "85%", delay: "3.5s", duration: "17s", height: "80px" },
  { id: 13, isGreen: true, left: "92%", delay: "6.5s", duration: "14s", height: "52px" },
  { id: 14, isGreen: false, left: "8%", delay: "5.5s", duration: "16s", height: "63px" },
  { id: 15, isGreen: true, left: "22%", delay: "1.2s", duration: "19s", height: "58px" },
  { id: 16, isGreen: false, left: "35%", delay: "4.2s", duration: "13s", height: "47px" },
  { id: 17, isGreen: true, left: "48%", delay: "2.8s", duration: "15s", height: "73px" },
  { id: 18, isGreen: true, left: "62%", delay: "7.5s", duration: "18s", height: "66px" },
  { id: 19, isGreen: false, left: "75%", delay: "0.8s", duration: "14s", height: "54px" },
  { id: 20, isGreen: true, left: "88%", delay: "3.8s", duration: "17s", height: "78px" },
  { id: 21, isGreen: false, left: "15%", delay: "6.2s", duration: "16s", height: "44px" },
  { id: 22, isGreen: true, left: "42%", delay: "1.8s", duration: "19s", height: "69px" },
  { id: 23, isGreen: true, left: "68%", delay: "5.2s", duration: "13s", height: "56px" },
  { id: 24, isGreen: false, left: "95%", delay: "2.2s", duration: "15s", height: "61px" },
];

// Pre-generated price data
const PRICE_DATA = [
  { id: 0, value: "42583.67", isGreen: true, left: "8%", delay: "0s" },
  { id: 1, value: "1847.23", isGreen: false, left: "18%", delay: "2s" },
  { id: 2, value: "31256.89", isGreen: true, left: "28%", delay: "4s" },
  { id: 3, value: "156.42", isGreen: true, left: "38%", delay: "6s" },
  { id: 4, value: "2891.56", isGreen: false, left: "48%", delay: "8s" },
  { id: 5, value: "45123.78", isGreen: true, left: "58%", delay: "1s" },
  { id: 6, value: "789.34", isGreen: false, left: "68%", delay: "3s" },
  { id: 7, value: "12456.91", isGreen: true, left: "78%", delay: "5s" },
  { id: 8, value: "3567.45", isGreen: true, left: "88%", delay: "7s" },
  { id: 9, value: "28934.12", isGreen: false, left: "15%", delay: "9s" },
  { id: 10, value: "567.89", isGreen: true, left: "35%", delay: "1.5s" },
  { id: 11, value: "19876.54", isGreen: true, left: "55%", delay: "3.5s" },
  { id: 12, value: "4521.67", isGreen: false, left: "75%", delay: "5.5s" },
  { id: 13, value: "38901.23", isGreen: true, left: "92%", delay: "7.5s" },
  { id: 14, value: "1234.56", isGreen: false, left: "5%", delay: "9.5s" },
];

const AuthLayout = ({ children }: { children: React.ReactNode }) => {
  const router = useRouter();
  const pathname = usePathname();
  const isSignUp = pathname === "/sign-up";

  const handleToggle = (toSignUp: boolean) => {
    if (toSignUp) {
      router.push("/sign-up");
    } else {
      router.push("/sign-in");
    }
  };

  const candles = useMemo(() => CANDLE_DATA, []);
  const priceNumbers = useMemo(() => PRICE_DATA, []);

  return (
    <div className="auth-page">
      {/* Enhanced Animated Background */}
      <div className="auth-bg">
        {/* Animated Grid */}
        <div className="trading-grid"></div>
        
        {/* Glowing Orbs */}
        <div className="glow-orbs">
          <div className="glow-orb glow-orb-1"></div>
          <div className="glow-orb glow-orb-2"></div>
          <div className="glow-orb glow-orb-3"></div>
        </div>
        
        {/* Floating Candlesticks */}
        <div className="floating-candles">
          {candles.map((candle) => (
            <div
              key={candle.id}
              className={`candle ${candle.isGreen ? "green" : "red"}`}
              style={{
                left: candle.left,
                animationDelay: candle.delay,
                animationDuration: candle.duration,
                height: candle.height,
              }}
            />
          ))}
        </div>

        {/* Floating Price Numbers */}
        <div className="price-numbers">
          {priceNumbers.map((price) => (
            <div
              key={price.id}
              className={`price-number ${price.isGreen ? "green" : "red"}`}
              style={{
                left: price.left,
                animationDelay: price.delay,
              }}
            >
              ${price.value}
            </div>
          ))}
        </div>
        
        {/* Pulse Rings */}
        <div className="pulse-rings">
          <div className="pulse-ring pulse-ring-1"></div>
          <div className="pulse-ring pulse-ring-2"></div>
          <div className="pulse-ring pulse-ring-3"></div>
        </div>
      </div>

      {/* Main Auth Container */}
      <div className={`auth-container ${isSignUp ? "right-panel-active" : ""}`}>
        {/* Sign Up Form Container */}
        <div className="form-container sign-up-container">
          {isSignUp && children}
        </div>

        {/* Sign In Form Container */}
        <div className="form-container sign-in-container">
          {!isSignUp && children}
        </div>

        {/* Overlay Container */}
        <div className="overlay-container">
          <div className="overlay">
            {/* Left Panel - Shows when on Sign Up */}
            <div className="overlay-panel overlay-left">
              <div className="panel-content">
                {/* Trading Visual Image */}
                <div className="trading-visual">
                  <Image 
                    src="https://images.unsplash.com/photo-1611974789855-9c2a0a7236a3?w=400&h=300&fit=crop" 
                    alt="Trading Charts"
                    width={400}
                    height={300}
                    unoptimized
                  />
                </div>
                
                {/* Animated Chart Line */}
                <div className="chart-visual">
                  <svg viewBox="0 0 200 100" preserveAspectRatio="none">
                    <path
                      className="chart-path"
                      d="M0 80 Q20 60 40 70 T80 40 T120 55 T160 30 T200 45"
                    />
                  </svg>
                </div>

                <h2>Welcome Back, Trader.</h2>
                <p>The market is moving fast. Sign in to track your portfolio&apos;s performance, review your latest buy/sell signals, and seize today&apos;s opportunities before they pass. Let&apos;s see what&apos;s trending.</p>
                
                {/* Animated Candlesticks */}
                <div className="candlestick-visual">
                  {[45, 60, 35, 55, 70, 40, 65].map((height, i) => (
                    <div
                      key={i}
                      className={`mini-candle ${i % 3 === 0 ? "red" : "green"}`}
                      style={{ 
                        height: `${height}px`,
                        "--delay": i
                      } as React.CSSProperties}
                    />
                  ))}
                </div>

                <div className="stats-preview">
                  <div className="stat">
                    <span className="stat-value">$2.4T</span>
                    <span className="stat-label">Daily Volume</span>
                  </div>
                  <div className="stat">
                    <span className="stat-value">150+</span>
                    <span className="stat-label">Markets</span>
                  </div>
                </div>
                
                <button className="ghost-btn" onClick={() => handleToggle(false)}>
                  <span>Sign In</span>
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M5 12h14M12 5l7 7-7 7" />
                  </svg>
                </button>
              </div>
            </div>

            {/* Right Panel - Shows when on Sign In */}
            <div className="overlay-panel overlay-right">
              <div className="panel-content">
                {/* Trading Visual Image */}
                <div className="trading-visual">
                  <Image 
                    src="https://images.unsplash.com/photo-1642790106117-e829e14a795f?w=400&h=300&fit=crop" 
                    alt="Crypto Trading"
                    width={400}
                    height={300}
                    unoptimized
                  />
                </div>

                {/* Animated Chart Line */}
                <div className="chart-visual">
                  <svg viewBox="0 0 200 100" preserveAspectRatio="none">
                    <path
                      className="chart-path"
                      d="M0 50 Q30 70 60 40 T100 60 T140 25 T180 45 T200 20"
                    />
                  </svg>
                </div>

                <h2>Don&apos;t Just Watch the Market—Master It.</h2>
                <p>Empower your financial journey with professional-grade tools. Join Market Pulse to unlock advanced heatmaps, set instant price alerts, and make confident moves with real-time signals. Your path to smart trading starts here.</p>
                
                {/* Animated Candlesticks */}
                <div className="candlestick-visual">
                  {[50, 35, 65, 45, 55, 70, 40].map((height, i) => (
                    <div
                      key={i}
                      className={`mini-candle ${i % 2 === 0 ? "green" : "red"}`}
                      style={{ 
                        height: `${height}px`,
                        "--delay": i
                      } as React.CSSProperties}
                    />
                  ))}
                </div>

                <div className="features-preview">
                  <div className="feature">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <path d="M22 12h-4l-3 9L9 3l-3 9H2" />
                    </svg>
                    <span>Real-time Data</span>
                  </div>
                  <div className="feature">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <path d="M12 2v20M17 5H9.5a3.5 3.5 0 000 7h5a3.5 3.5 0 010 7H6" />
                    </svg>
                    <span>Smart Trading</span>
                  </div>
                </div>
                
                <button className="ghost-btn" onClick={() => handleToggle(true)}>
                  <span>Sign Up</span>
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M5 12h14M12 5l7 7-7 7" />
                  </svg>
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default AuthLayout;
