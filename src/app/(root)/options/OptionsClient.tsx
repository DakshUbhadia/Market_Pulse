'use client';

import { useEffect } from 'react';
import { usePageContext } from '@/context/PageContext';
import OptionsRadarPanel from '@/components/analysis/OptionsRadarPanel';
import OptionsScopePanel from '@/components/analysis/OptionsScopePanel';
import TomHougaardAlert from '@/components/analysis/TomHougaardAlert';

/**
 * OptionsClient Component
 *
 * Displays F&O (Futures & Options) focused market analysis using the F_O_stocks list.
 * This is a specialized variant of MarketScopeClient optimized for derivatives trading.
 *
 * Features:
 * - Momentum radar analysis for F&O eligible stocks
 * - Market scope heatmap and sector analysis for F&O basket
 * - Tom Hougaard alert system (defaulting to Indian market)
 * - Exclusive page registration to prevent Yahoo Finance rate limiting
 */
export default function OptionsClient() {
  const { setExclusivePage, clearExclusivePage } = usePageContext();

  // Register as exclusive page to pause background watchlist fetches
  // This prevents Yahoo Finance rate limiting which causes price freezes in simulator
  useEffect(() => {
    setExclusivePage('options');
    return () => {
      clearExclusivePage();
    };
  }, [setExclusivePage, clearExclusivePage]);

  return (
    <div className="container mx-auto p-6 max-w-7xl space-y-6">
      {/* Tom Hougaard Strategy Alert - At the TOP, defaulting to Indian market */}
      <TomHougaardAlert market="IN" />

      {/* Options Momentum Radar - Real-time momentum detection for F&O stocks */}
      <OptionsRadarPanel />

      {/* Options Market Scope - Sector heatmap and R-Factor analysis for F&O basket */}
      <OptionsScopePanel />
    </div>
  );
}
