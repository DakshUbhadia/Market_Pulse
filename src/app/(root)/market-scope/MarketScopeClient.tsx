'use client';

import { useState } from 'react';
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Globe, Building2 } from 'lucide-react';
import type { MarketType } from '@/lib/markets';
import MomentumRadarPanel from '@/components/analysis/MomentumRadarPanel';
import MarketScopePanel from '@/components/analysis/MarketScopePanel';
import TomHougaardAlert from '@/components/analysis/TomHougaardAlert';

export default function MarketScopeClient() {
  // Default to Indian market (IN) when user navigates to market-scope
  const [market, setMarket] = useState<MarketType>('IN');

  return (
    <div className="container mx-auto p-6 max-w-7xl space-y-6">
      {/* Tom Hougaard Strategy Alert - At the TOP */}
      <TomHougaardAlert market={market} />

      <div className="flex items-center justify-end">
        <Tabs value={market} onValueChange={(v) => setMarket(v as MarketType)} className="w-full sm:w-auto">
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
