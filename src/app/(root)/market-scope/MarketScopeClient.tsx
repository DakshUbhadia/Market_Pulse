'use client';

import { useState, useEffect } from 'react';
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Globe, Building2 } from 'lucide-react';
import { usePageContext } from '@/context/PageContext';
import type { MarketType } from '@/lib/constants';
import MomentumRadarPanel from '@/components/analysis/MomentumRadarPanel';
import MarketScopePanel from '@/components/analysis/MarketScopePanel';
import TomHougaardAlert from '@/components/analysis/TomHougaardAlert';

const MARKET_SCOPE_STORAGE_KEY = 'marketScope_selectedMarket';

export default function MarketScopeClient() {
  // Initialize from localStorage or default to Indian market (IN)
  const [market, setMarket] = useState<MarketType>(() => {
    if (typeof globalThis.window !== 'undefined') {
      const saved = localStorage.getItem(MARKET_SCOPE_STORAGE_KEY);
      if (saved === 'US' || saved === 'IN') return saved;
    }
    return 'IN';
  });
  const { setExclusivePage, clearExclusivePage } = usePageContext();

  // Handle market change - only updates when user manually switches
  const handleMarketChange = (newMarket: string) => {
    const marketType = newMarket as MarketType;
    setMarket(marketType);
    localStorage.setItem(MARKET_SCOPE_STORAGE_KEY, marketType);
  };

  // Register as exclusive page to pause background watchlist fetches
  // This prevents Yahoo Finance rate limiting which causes price freezes in simulator
  useEffect(() => {
    setExclusivePage('market-scope');
    return () => {
      clearExclusivePage();
    };
  }, [setExclusivePage, clearExclusivePage]);

  return (
    <div className="container mx-auto p-6 max-w-7xl space-y-6">
      {/* Tom Hougaard Strategy Alert - At the TOP */}
      <TomHougaardAlert market={market} />

      <div className="flex items-center justify-end">
        <Tabs value={market} onValueChange={handleMarketChange} className="w-full sm:w-auto">
          <TabsList className="grid w-full grid-cols-2 sm:w-[280px] bg-muted/30">
            <TabsTrigger
              value="US"
              className="flex items-center gap-2 data-[state=active]:bg-cyan-500/20 data-[state=active]:text-cyan-300"
            >
              <Globe className="h-4 w-4" />
              American
            </TabsTrigger>
            <TabsTrigger
              value="IN"
              className="flex items-center gap-2 data-[state=active]:bg-cyan-500/20 data-[state=active]:text-cyan-300"
            >
              <Building2 className="h-4 w-4" />
              Indian
            </TabsTrigger>
          </TabsList>
        </Tabs>
      </div>

      <MomentumRadarPanel market={market} showMarketTabs={false} />
      <MarketScopePanel market={market} showMarketTabs={false} />
    </div>
  );
}
