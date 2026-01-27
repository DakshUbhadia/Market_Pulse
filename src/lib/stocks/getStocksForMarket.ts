import { BSE_STOCKS, US_DEFAULT_STOCKS, type StockListItem } from '@/lib/constants';
import type { MarketType } from '@/lib/markets';

export const getStocksForMarket = (market: MarketType): StockListItem[] => {
  if (market === 'US') {
    return US_DEFAULT_STOCKS ?? [];
  }

  // For Indian market, use BSE stocks (with .BO suffix for Yahoo Finance)
  return (BSE_STOCKS ?? []).map((s) => ({
    ...s,
    symbol: s.symbol.endsWith('.BO') ? s.symbol : `${s.symbol}.BO`,
  }));
};
