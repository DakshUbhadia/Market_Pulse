import React from "react";
import "./landing.css";

import {
  LandingHeader,
  HeroSection,
  MarketSnapshotSection,
  DetailedStockAnalysisSection,
  FeatureAlerts,
  DailyNewsSummarySection,
  FeatureAnalysis,
  WatchlistSection,
  CTASection,
  LandingFooter,
  GoldParticles,
} from "@/components/landing";

export default function LandingPage() {
  return (
    <div className="landing-page">
      <GoldParticles />
      <LandingHeader />
      <HeroSection />
      <MarketSnapshotSection />
      <DetailedStockAnalysisSection />
      <FeatureAlerts />
      <DailyNewsSummarySection />
      <FeatureAnalysis />
      <WatchlistSection />
      <CTASection />
      <LandingFooter />
    </div>
  );
}
