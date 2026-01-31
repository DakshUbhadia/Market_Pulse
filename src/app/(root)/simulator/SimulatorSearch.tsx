'use client';

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useRouter } from 'next/navigation';
import { Loader2, Search, TrendingUp } from 'lucide-react';
import type { MarketType } from '@/lib/actions/trading.actions';

import {
  CommandDialog,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from '@/components/ui/command';

import { searchStocks } from '@/lib/actions/finnhub.actions';

type StockResult = {
  symbol: string;
  name: string;
  exchange: string;
  type: string;
};

type SimulatorSearchProps = {
  readonly open: boolean;
  readonly onOpenChange: (open: boolean) => void;
  readonly market: MarketType;
};

// Default stocks by market
const DEFAULT_INDIAN_STOCKS: StockResult[] = [
  { symbol: 'RELIANCE', name: 'Reliance Industries', exchange: 'NSE', type: 'Stock' },
  { symbol: 'HDFCBANK', name: 'HDFC Bank', exchange: 'NSE', type: 'Stock' },
  { symbol: 'TCS', name: 'Tata Consultancy Services', exchange: 'NSE', type: 'Stock' },
  { symbol: 'INFY', name: 'Infosys', exchange: 'NSE', type: 'Stock' },
  { symbol: 'ICICIBANK', name: 'ICICI Bank', exchange: 'NSE', type: 'Stock' },
  { symbol: 'TATASTEEL', name: 'Tata Steel', exchange: 'NSE', type: 'Stock' },
  { symbol: 'SBIN', name: 'State Bank of India', exchange: 'NSE', type: 'Stock' },
  { symbol: 'WIPRO', name: 'Wipro', exchange: 'NSE', type: 'Stock' },
];

const DEFAULT_US_STOCKS: StockResult[] = [
  { symbol: 'AAPL', name: 'Apple', exchange: 'NASDAQ', type: 'Stock' },
  { symbol: 'NVDA', name: 'NVIDIA', exchange: 'NASDAQ', type: 'Stock' },
  { symbol: 'TSLA', name: 'Tesla', exchange: 'NASDAQ', type: 'Stock' },
  { symbol: 'GOOGL', name: 'Alphabet (Google)', exchange: 'NASDAQ', type: 'Stock' },
  { symbol: 'AMZN', name: 'Amazon', exchange: 'NASDAQ', type: 'Stock' },
  { symbol: 'META', name: 'Meta', exchange: 'NASDAQ', type: 'Stock' },
  { symbol: 'MSFT', name: 'Microsoft', exchange: 'NASDAQ', type: 'Stock' },
  { symbol: 'AMD', name: 'AMD', exchange: 'NASDAQ', type: 'Stock' },
];

// Helper to check if exchange is Indian
function isIndianExchange(exchange: string): boolean {
  const exch = (exchange || '').toUpperCase();
  return exch === 'BSE' || exch === 'NSE' || exch === 'BO' || exch === 'NS' || exch === 'IN';
}

export default function SimulatorSearch({
  open,
  onOpenChange,
  market,
}: SimulatorSearchProps) {
  const router = useRouter();
  const [query, setQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [stocks, setStocks] = useState<StockResult[]>([]);
  const lastRequestId = useRef(0);

  // Get default stocks based on market
  const defaultStocks = market === 'IN' ? DEFAULT_INDIAN_STOCKS : DEFAULT_US_STOCKS;

  // Keyboard shortcut
  useEffect(() => {
    const onKeyDown = (e: KeyboardEvent) => {
      const nav = navigator as Navigator & { userAgentData?: { platform?: string } };
      const platform = (nav.userAgentData?.platform ?? nav.platform ?? '').toString();
      const isMac = platform.toLowerCase().includes('mac');
      const isK = e.key.toLowerCase() === 's';
      const modifier = isMac ? e.metaKey : e.ctrlKey;

      if (modifier && isK && !open) {
        e.preventDefault();
        onOpenChange(true);
      }

      if (e.key === 'Escape' && open) {
        e.preventDefault();
        onOpenChange(false);
      }
    };

    globalThis.addEventListener('keydown', onKeyDown);
    return () => globalThis.removeEventListener('keydown', onKeyDown);
  }, [open, onOpenChange]);

  // Search stocks when query changes
  useEffect(() => {
    if (!open) return;

    const requestId = ++lastRequestId.current;
    const trimmed = query.trim();
    setLoading(true);

    const timer = globalThis.setTimeout(async () => {
      try {
        const results = await searchStocks(trimmed || undefined);
        if (lastRequestId.current === requestId) {
          // Filter by market
          const filtered = results.filter(r => {
            const isIndian = isIndianExchange(r.exchange);
            return market === 'IN' ? isIndian : !isIndian;
          });
          
          setStocks(filtered.map(r => ({
            symbol: r.symbol,
            name: r.name,
            exchange: r.exchange,
            type: r.type,
          })));
        }
      } catch (error) {
        console.error('Error in stock search:', error);
        if (lastRequestId.current === requestId) {
          setStocks([]);
        }
      } finally {
        if (lastRequestId.current === requestId) {
          setLoading(false);
        }
      }
    }, 300);

    return () => globalThis.clearTimeout(timer);
  }, [open, query, market]);

  const handleQueryChange = useCallback((value: string) => {
    setQuery(value);
  }, []);

  const handleSelectStock = useCallback((value: string) => {
    onOpenChange(false);
    
    // Find the stock to get exchange
    const stock = stocks.find(s => s.symbol === value) || 
                  defaultStocks.find(s => s.symbol === value);
    const exchange = stock?.exchange || (market === 'IN' ? 'NSE' : 'NASDAQ');
    
    router.push(`/simulator/${encodeURIComponent(value.toUpperCase())}?exchange=${exchange}`);
  }, [onOpenChange, router, stocks, defaultStocks, market]);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();

    const base: StockResult[] =
      stocks.length > 0 ? stocks : defaultStocks;

    if (!q) return base;
    return base.filter(
      (s) => s.symbol.toLowerCase().includes(q) || s.name.toLowerCase().includes(q)
    );
  }, [query, stocks, defaultStocks]);

  return (
    <CommandDialog open={open} onOpenChange={onOpenChange}>
      <div className="flex items-center justify-between gap-3 border-b px-4 py-3">
        <div className="min-w-0">
          <div className="text-sm font-semibold text-foreground flex items-center gap-2">
            <TrendingUp className={`h-4 w-4 ${market === 'IN' ? 'text-yellow-500' : 'text-blue-500'}`} />
            Search {market === 'IN' ? 'Indian' : 'US'} Stocks to Trade
          </div>
          <div className="text-xs text-muted-foreground">
            Find stocks and start paper trading
          </div>
        </div>
        <div className="shrink-0 flex items-center gap-2">
          <span className={`text-xs px-2 py-0.5 rounded ${market === 'IN' ? 'bg-yellow-500/20 text-yellow-500' : 'bg-blue-500/20 text-blue-500'}`}>
            {market === 'IN' ? '🇮🇳 India' : '🇺🇸 US'}
          </span>
          <span className="text-xs text-muted-foreground">Esc</span>
        </div>
      </div>
      <CommandInput
        placeholder={`Search ${market === 'IN' ? 'NSE/BSE' : 'NASDAQ/NYSE'} stocks…`}
        value={query}
        onValueChange={handleQueryChange}
        icon={<Search className={`h-4 w-4 ${market === 'IN' ? 'text-yellow-500/70' : 'text-blue-500/70'}`} />}
        className="placeholder:text-muted-foreground"
      />

      <CommandList>
        {loading ? (
          <div className="flex items-center justify-center gap-2 p-8 text-sm text-muted-foreground">
            <Loader2 className={`h-4 w-4 animate-spin ${market === 'IN' ? 'text-yellow-500/80' : 'text-blue-500/80'}`} />
            <span>Searching…</span>
          </div>
        ) : (
          <>
            {filtered.length === 0 ? (
              <CommandEmpty>No {market === 'IN' ? 'Indian' : 'US'} stocks found.</CommandEmpty>
            ) : null}
            <CommandGroup heading={`${market === 'IN' ? 'Indian' : 'US'} Stocks`}>
              {filtered.map((stock) => (
                <CommandItem
                  key={stock.symbol}
                  value={stock.symbol}
                  onSelect={handleSelectStock}
                  className={`group rounded-md px-3 py-2 ${market === 'IN' ? 'hover:bg-yellow-500/10' : 'hover:bg-blue-500/10'}`}
                >
                  <span className={`inline-flex h-7 w-14 items-center justify-center rounded-md border text-xs font-semibold ${
                    market === 'IN' 
                      ? 'border-yellow-500/15 bg-yellow-500/10 text-yellow-500'
                      : 'border-blue-500/15 bg-blue-500/10 text-blue-500'
                  }`}>
                    {stock.symbol}
                  </span>
                  <span className="flex min-w-0 flex-1 flex-col text-left ml-3">
                    <span className="truncate text-sm text-foreground">{stock.name}</span>
                    <span className="truncate text-xs text-muted-foreground">
                      {stock.exchange}
                    </span>
                  </span>
                  <span className={`ml-2 text-xs ${market === 'IN' ? 'text-yellow-500' : 'text-blue-500'}`}>
                    Trade →
                  </span>
                </CommandItem>
              ))}
            </CommandGroup>
          </>
        )}
      </CommandList>
    </CommandDialog>
  );
}
