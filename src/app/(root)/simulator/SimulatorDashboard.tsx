'use client';

import { useState, useEffect, useCallback, useRef, useMemo } from 'react';
import Link from 'next/link';
import { usePageContext } from '@/context/PageContext';
import { 
  getPortfolioSummary, 
  getUserBalance, 
  getTransactionHistory,
  resetPortfolio,
  type TransactionHistoryItem,
  type MarketType
} from '@/lib/actions/trading.actions';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { 
  Wallet, 
  TrendingUp, 
  TrendingDown, 
  PieChart, 
  History, 
  RefreshCw,
  AlertCircle,
  ArrowUpRight,
  RotateCcw,
  Globe,
  Building2,
  Calendar,
  Search
} from 'lucide-react';
import TradingLoader from '@/components/ui/TradingLoader';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import SimulatorSearch from './SimulatorSearch';

interface Holding {
  symbol: string;
  company: string;
  exchange: string;
  quantity: number;
  averageBuyPrice: number;
  currentPrice: number;
  currentValue: number;
  totalInvested: number;
  pnl: number;
  pnlPercent: number;
}

// Default balances
const DEFAULT_INDIAN_BALANCE = 1000000; // ₹10,00,000
const DEFAULT_US_BALANCE = 100000; // $100,000

// Currency formatting helpers
function isIndianMarket(market: MarketType): boolean {
  return market === 'IN';
}

function formatPrice(price: number, market: MarketType): string {
  if (isIndianMarket(market)) {
    return `₹${price.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  }
  return `$${price.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

function formatPnL(price: number, market: MarketType): string {
  const prefix = price >= 0 ? '+' : '';
  if (isIndianMarket(market)) {
    return `${prefix}₹${Math.abs(price).toLocaleString('en-IN', { maximumFractionDigits: 2 })}`;
  }
  return `${prefix}$${Math.abs(price).toLocaleString('en-US', { maximumFractionDigits: 2 })}`;
}

function getTimezoneForMarket(market: MarketType): string {
  return isIndianMarket(market) ? 'Asia/Kolkata' : 'America/New_York';
}

function getLocaleForMarket(market: MarketType): string {
  return isIndianMarket(market) ? 'en-IN' : 'en-US';
}

// SSE quote update type
type StreamQuoteUpdate = {
  currentPrice: number;
  openPrice?: number;
  percentChange?: number;
};

// Chunk array helper for SSE batching
const chunkArray = <T,>(items: T[], chunkSize: number): T[][] => {
  if (chunkSize <= 0) return [items];
  const out: T[][] = [];
  for (let i = 0; i < items.length; i += chunkSize) {
    out.push(items.slice(i, i + chunkSize));
  }
  return out;
};

export default function SimulatorDashboard() {
  const { setExclusivePage, clearExclusivePage } = usePageContext();
  
  const [market, setMarket] = useState<MarketType>('IN'); // Default to Indian market
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [resetting, setResetting] = useState(false);

  // State for portfolio data
  const [indianBalance, setIndianBalance] = useState(DEFAULT_INDIAN_BALANCE);
  const [usBalance, setUsBalance] = useState(DEFAULT_US_BALANCE);
  const [portfolioValue, setPortfolioValue] = useState(0);
  const [totalPnL, setTotalPnL] = useState(0);
  const [holdings, setHoldings] = useState<Holding[]>([]);
  const [transactions, setTransactions] = useState<TransactionHistoryItem[]>([]);
  const [allTodayTransactions, setAllTodayTransactions] = useState<TransactionHistoryItem[]>([]);
  const [allTransactions, setAllTransactions] = useState<TransactionHistoryItem[]>([]);

  // SSE refs
  const eventSourcesRef = useRef<EventSource[]>([]);
  const priceMapRef = useRef<Map<string, StreamQuoteUpdate>>(new Map());
  
  // Search state
  const [showSearch, setShowSearch] = useState(false);
  
  // Register as exclusive page to pause background watchlist fetches
  useEffect(() => {
    setExclusivePage('simulator');
    return () => {
      clearExclusivePage();
    };
  }, [setExclusivePage, clearExclusivePage]);

  // Get current balance based on market
  const balance = market === 'IN' ? indianBalance : usBalance;
  const defaultBalance = market === 'IN' ? DEFAULT_INDIAN_BALANCE : DEFAULT_US_BALANCE;

  // Calculate net worth and P&L
  const netWorth = balance + portfolioValue;
  const totalPnLPercent = defaultBalance > 0 ? ((netWorth - defaultBalance) / defaultBalance) * 100 : 0;

  // Calculate today's P/L from completed sell transactions
  const todayPnL = useMemo(() => {
    // For today's P/L, we calculate based on SELL transactions
    // Each sell has a realized P/L = (sellPrice - avgBuyPrice) * quantity
    // This requires knowing the average buy price at time of sale
    
    // Simple calculation: Sum of all trades today
    // BUY = money spent (negative), SELL = money received (positive)
    return allTodayTransactions.reduce((acc, tx) => {
      if (tx.type === 'SELL') {
        return acc + tx.totalAmount; // Money received
      } else if (tx.type === 'BUY') {
        return acc - tx.totalAmount; // Money spent
      }
      return acc;
    }, 0);
  }, [allTodayTransactions]);

  const todayTradeCount = allTodayTransactions.length;

  // Calculate daily profit history from all transactions
  const profitHistory = useMemo(() => {
    // Group transactions by date and calculate net P/L per day
    const dailyMap = new Map<string, { buys: number; sells: number; date: Date }>();
    
    allTransactions.forEach(tx => {
      const txDate = new Date(tx.timestamp);
      const dateKey = txDate.toISOString().slice(0, 10); // YYYY-MM-DD
      
      if (!dailyMap.has(dateKey)) {
        dailyMap.set(dateKey, { buys: 0, sells: 0, date: txDate });
      }
      
      const entry = dailyMap.get(dateKey)!;
      if (tx.type === 'SELL') {
        entry.sells += tx.totalAmount;
      } else if (tx.type === 'BUY') {
        entry.buys += tx.totalAmount;
      }
    });
    
    // Convert to array and calculate net P/L (sells - buys = cash flow)
    return Array.from(dailyMap.entries())
      .map(([dateKey, data]) => ({
        date: dateKey,
        displayDate: data.date,
        pnl: data.sells - data.buys, // Positive = net inflow, Negative = net outflow
        buys: data.buys,
        sells: data.sells,
      }))
      .sort((a, b) => b.date.localeCompare(a.date)) // Most recent first
      .slice(0, 30); // Last 30 days with activity
  }, [allTransactions]);

  // Fetch data based on market
  const fetchData = useCallback(async (showRefreshing = false) => {
    if (showRefreshing) setRefreshing(true);
    
    try {
      const [balanceResult, portfolioResult, txResult, allTxResult] = await Promise.all([
        getUserBalance(market),
        getPortfolioSummary(market),
        getTransactionHistory(1, 10, undefined, market),
        getTransactionHistory(1, 500, undefined, market), // Get more for profit history
      ]);

      if (balanceResult.success) {
        setIndianBalance(balanceResult.indianBalance);
        setUsBalance(balanceResult.usBalance);
      }

      if (portfolioResult.success) {
        setHoldings(portfolioResult.holdings);
        setPortfolioValue(portfolioResult.totalValue);
        setTotalPnL(portfolioResult.totalPnL);
      }

      if (txResult.success) {
        setTransactions(txResult.transactions);
      }
      
      // Store all transactions for profit history & filter today's for daily P/L
      if (allTxResult.success) {
        setAllTransactions(allTxResult.transactions);
        
        const today = new Date();
        const todayStart = new Date(today.getFullYear(), today.getMonth(), today.getDate()).getTime();
        const todayTx = allTxResult.transactions.filter(tx => 
          new Date(tx.timestamp).getTime() >= todayStart
        );
        setAllTodayTransactions(todayTx);
      }
    } catch (error) {
      console.error('Error fetching dashboard data:', error);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [market]);

  // Fetch data when market changes
  useEffect(() => {
    setLoading(true);
    fetchData();
  }, [fetchData]);

  // Track holdings for SSE
  const holdingsRef = useRef<Holding[]>([]);
  useEffect(() => {
    holdingsRef.current = holdings;
  }, [holdings]);

  // SSE for live price updates
  useEffect(() => {
    if (holdings.length === 0) return;

    // Close existing connections
    eventSourcesRef.current.forEach(es => es.close());
    eventSourcesRef.current = [];

    // Prepare items for SSE
    const items = holdings.map(h => ({
      symbol: h.symbol,
      exchange: h.exchange
    }));

    // Chunk into batches of 50
    const chunks = chunkArray(items, 50);

    const handleQuotesEvent = (event: MessageEvent) => {
      try {
        const data = JSON.parse(event.data) as {
          quotes: Array<{
            symbol: string;
            currentPrice?: number;
            openPrice?: number;
            percentChange?: number;
          }>;
        };

        // Update price map
        data.quotes.forEach(q => {
          if (q.symbol && typeof q.currentPrice === 'number') {
            priceMapRef.current.set(q.symbol.toUpperCase(), {
              currentPrice: q.currentPrice,
              openPrice: q.openPrice,
              percentChange: q.percentChange,
            });
          }
        });

        // Update holdings with new prices using ref to avoid dependency
        setHoldings(prevHoldings => {
          let changed = false;
          const newHoldings = prevHoldings.map(h => {
            const update = priceMapRef.current.get(h.symbol.toUpperCase());
            if (update && update.currentPrice !== h.currentPrice) {
              changed = true;
              const currentValue = h.quantity * update.currentPrice;
              const pnl = currentValue - h.totalInvested;
              const pnlPercent = h.totalInvested > 0 ? (pnl / h.totalInvested) * 100 : 0;
              return {
                ...h,
                currentPrice: update.currentPrice,
                currentValue,
                pnl,
                pnlPercent,
              };
            }
            return h;
          });
          
          if (changed) {
            // Recalculate totals
            const newPortfolioValue = newHoldings.reduce((sum, h) => sum + h.currentValue, 0);
            const newTotalPnL = newHoldings.reduce((sum, h) => sum + h.pnl, 0);
            setPortfolioValue(newPortfolioValue);
            setTotalPnL(newTotalPnL);
          }
          
          return changed ? newHoldings : prevHoldings;
        });
      } catch {
        // Ignore parse errors
      }
    };

    // Create SSE connections with automatic reconnection
    const createEventSource = (chunk: typeof items, retryCount = 0) => {
      const itemsParam = encodeURIComponent(JSON.stringify(chunk));
      const url = `/api/quotes/stream?items=${itemsParam}`;
      const eventSource = new EventSource(url);
      
      eventSource.addEventListener('quotes', handleQuotesEvent);
      
      eventSource.addEventListener('error', () => {
        // Auto-reconnect with exponential backoff (max 30 seconds)
        const delay = Math.min(1000 * Math.pow(2, retryCount), 30000);
        eventSource.close();
        
        // Remove from refs
        const idx = eventSourcesRef.current.indexOf(eventSource);
        if (idx > -1) eventSourcesRef.current.splice(idx, 1);
        
        // Reconnect after delay
        setTimeout(() => {
          if (holdingsRef.current.length > 0) {
            const newEs = createEventSource(chunk, retryCount + 1);
            eventSourcesRef.current.push(newEs);
          }
        }, delay);
      });
      
      return eventSource;
    };

    chunks.forEach((chunk) => {
      const eventSource = createEventSource(chunk);
      eventSourcesRef.current.push(eventSource);
    });

    return () => {
      eventSourcesRef.current.forEach(es => es.close());
      eventSourcesRef.current = [];
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [holdings.length, market]);

  const handleReset = async () => {
    const marketLabel = market === 'IN' ? 'Indian' : 'American';
    const balanceMsg = market === 'IN' ? '₹10,00,000' : '$100,000';
    
    if (!confirm(`Are you sure you want to reset your ${marketLabel} portfolio? This will clear all ${marketLabel} holdings and restore your balance to ${balanceMsg}.`)) {
      return;
    }

    setResetting(true);
    try {
      const result = await resetPortfolio(market);
      if (result.success) {
        await fetchData();
      }
    } catch (error) {
      console.error('Error resetting portfolio:', error);
    } finally {
      setResetting(false);
    }
  };

  const handleMarketChange = (newMarket: string) => {
    setMarket(newMarket as MarketType);
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <TradingLoader />
      </div>
    );
  }

  return (
    <div className="space-y-4 sm:space-y-6 p-4 sm:p-6">
      {/* Header with Market Toggle */}
      <div className="flex flex-col gap-4">
        <div>
          <h1 className="text-xl sm:text-2xl font-bold text-foreground">Paper Trading Simulator</h1>
          <p className="text-xs sm:text-sm text-muted-foreground mt-1">
            Practice trading with virtual money. No risk, real learning.
          </p>
        </div>
        
        <div className="flex flex-col sm:flex-row sm:items-center gap-3 sm:gap-4">
          {/* Market Toggle */}
          <Tabs value={market} onValueChange={handleMarketChange}>
            <TabsList className="bg-muted/50 w-full sm:w-auto grid grid-cols-2 sm:flex">
              <TabsTrigger value="IN" className="data-[state=active]:bg-yellow-500/20 data-[state=active]:text-yellow-500 text-xs sm:text-sm">
                <Building2 className="h-3 w-3 sm:h-4 sm:w-4 mr-1.5 sm:mr-2" />
                India
              </TabsTrigger>
              <TabsTrigger value="US" className="data-[state=active]:bg-blue-500/20 data-[state=active]:text-blue-500 text-xs sm:text-sm">
                <Globe className="h-3 w-3 sm:h-4 sm:w-4 mr-1.5 sm:mr-2" />
                US
              </TabsTrigger>
            </TabsList>
          </Tabs>

          <div className="flex flex-wrap gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setShowSearch(true)}
              className="text-yellow-500 hover:text-yellow-600 hover:bg-yellow-500/10 text-xs sm:text-sm flex-1 sm:flex-none"
            >
              <Search className="h-3 w-3 sm:h-4 sm:w-4 mr-1.5 sm:mr-2" />
              Search Stock
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => fetchData(true)}
              disabled={refreshing}
              className="text-xs sm:text-sm"
            >
              <RefreshCw className={`h-3 w-3 sm:h-4 sm:w-4 mr-1.5 sm:mr-2 ${refreshing ? 'animate-spin' : ''}`} />
              Refresh
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={handleReset}
              disabled={resetting}
              className="text-red-500 hover:text-red-600 hover:bg-red-500/10 text-xs sm:text-sm"
            >
              <RotateCcw className={`h-3 w-3 sm:h-4 sm:w-4 mr-1.5 sm:mr-2 ${resetting ? 'animate-spin' : ''}`} />
              Reset
            </Button>
          </div>
        </div>
      </div>
      
      {/* Simulator Search Modal */}
      <SimulatorSearch 
        open={showSearch} 
        onOpenChange={setShowSearch} 
        market={market}
      />

      {/* Scoreboard Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4">
        {/* Net Worth */}
        <Card className={`border-border/30 bg-linear-to-br ${market === 'IN' ? 'from-yellow-500/10' : 'from-blue-500/10'} to-transparent`}>
          <CardHeader className="pb-1 sm:pb-2 p-3 sm:p-6">
            <CardTitle className="text-[10px] sm:text-sm font-medium text-muted-foreground flex items-center gap-1 sm:gap-2">
              <PieChart className="h-3 w-3 sm:h-4 sm:w-4" />
              <span className="truncate">Net Worth ({market === 'IN' ? 'India' : 'US'})</span>
            </CardTitle>
          </CardHeader>
          <CardContent className="p-3 sm:p-6 pt-0">
            <div className="text-lg sm:text-2xl font-bold text-foreground font-mono truncate">
              {formatPrice(netWorth, market)}
            </div>
            <div className={`text-[10px] sm:text-sm mt-0.5 sm:mt-1 flex items-center gap-0.5 sm:gap-1 ${totalPnLPercent >= 0 ? 'text-green-500' : 'text-red-500'}`}>
              {totalPnLPercent >= 0 ? <TrendingUp className="h-2.5 w-2.5 sm:h-3 sm:w-3" /> : <TrendingDown className="h-2.5 w-2.5 sm:h-3 sm:w-3" />}
              {totalPnLPercent >= 0 ? '+' : ''}{totalPnLPercent.toFixed(2)}%
            </div>
          </CardContent>
        </Card>

        {/* Available Cash */}
        <Card className="border-border/30 bg-linear-to-br from-green-500/10 to-transparent">
          <CardHeader className="pb-1 sm:pb-2 p-3 sm:p-6">
            <CardTitle className="text-[10px] sm:text-sm font-medium text-muted-foreground flex items-center gap-1 sm:gap-2">
              <Wallet className="h-3 w-3 sm:h-4 sm:w-4" />
              Available Cash
            </CardTitle>
          </CardHeader>
          <CardContent className="p-3 sm:p-6 pt-0">
            <div className="text-lg sm:text-2xl font-bold text-foreground font-mono truncate">
              {formatPrice(balance, market)}
            </div>
            <div className="text-[10px] sm:text-sm text-muted-foreground mt-0.5 sm:mt-1">
              Ready to invest
            </div>
          </CardContent>
        </Card>

        {/* Total P&L */}
        <Card className={`border-border/30 bg-linear-to-br ${totalPnL >= 0 ? 'from-green-500/10' : 'from-red-500/10'} to-transparent`}>
          <CardHeader className="pb-1 sm:pb-2 p-3 sm:p-6">
            <CardTitle className="text-[10px] sm:text-sm font-medium text-muted-foreground flex items-center gap-1 sm:gap-2">
              {totalPnL >= 0 ? <TrendingUp className="h-3 w-3 sm:h-4 sm:w-4" /> : <TrendingDown className="h-3 w-3 sm:h-4 sm:w-4" />}
              Total P&L
            </CardTitle>
          </CardHeader>
          <CardContent className="p-3 sm:p-6 pt-0">
            <div className={`text-lg sm:text-2xl font-bold font-mono truncate ${totalPnL >= 0 ? 'text-green-500' : 'text-red-500'}`}>
              {formatPnL(totalPnL, market)}
            </div>
            <div className="text-[10px] sm:text-sm text-muted-foreground mt-0.5 sm:mt-1">
              Unrealized
            </div>
          </CardContent>
        </Card>

        {/* Today's P&L */}
        <Card className={`border-border/30 bg-linear-to-br ${todayPnL >= 0 ? 'from-emerald-500/10' : 'from-orange-500/10'} to-transparent`}>
          <CardHeader className="pb-1 sm:pb-2 p-3 sm:p-6">
            <CardTitle className="text-[10px] sm:text-sm font-medium text-muted-foreground flex items-center gap-1 sm:gap-2">
              <Calendar className="h-3 w-3 sm:h-4 sm:w-4" />
              Today&apos;s Activity
            </CardTitle>
          </CardHeader>
          <CardContent className="p-3 sm:p-6 pt-0">
            <div className={`text-lg sm:text-2xl font-bold font-mono truncate ${todayPnL >= 0 ? 'text-emerald-500' : 'text-orange-500'}`}>
              {formatPnL(todayPnL, market)}
            </div>
            <div className="text-[10px] sm:text-sm text-muted-foreground mt-0.5 sm:mt-1">
              {todayTradeCount} trade{todayTradeCount === 1 ? '' : 's'}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Holdings Table */}
      <Card className="border-border/30">
        <CardHeader className="p-4 sm:p-6">
          <div className="flex items-center justify-between">
            <CardTitle className="text-base sm:text-lg font-semibold flex items-center gap-2">
              <PieChart className={`h-4 w-4 sm:h-5 sm:w-5 ${market === 'IN' ? 'text-yellow-500' : 'text-blue-500'}`} />
              {market === 'IN' ? 'Indian' : 'US'} Holdings
            </CardTitle>
            {holdings.length > 0 && (
              <span className="text-[10px] sm:text-xs text-green-500 flex items-center gap-1">
                <span className="w-1.5 h-1.5 sm:w-2 sm:h-2 bg-green-500 rounded-full animate-pulse"></span>
                Live
              </span>
            )}
          </div>
        </CardHeader>
        <CardContent className="p-4 sm:p-6 pt-0 overflow-x-auto">
          {holdings.length === 0 ? (
            <div className="text-center py-8 sm:py-12">
              <AlertCircle className="h-10 w-10 sm:h-12 sm:w-12 mx-auto text-muted-foreground mb-3 sm:mb-4" />
              <h3 className="text-base sm:text-lg font-semibold text-foreground mb-2">
                Your {market === 'IN' ? 'Indian' : 'US'} portfolio is empty
              </h3>
              <p className="text-xs sm:text-sm text-muted-foreground mb-4">
                Find profitable trades and start building your portfolio.
              </p>
              <Link href="/market-scope">
                <Button className={`${market === 'IN' ? 'bg-yellow-500 hover:bg-yellow-600' : 'bg-blue-500 hover:bg-blue-600'} text-black text-xs sm:text-sm`}>
                  Explore Market Scope
                  <ArrowUpRight className="h-3 w-3 sm:h-4 sm:w-4 ml-2" />
                </Button>
              </Link>
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="text-xs sm:text-sm">Symbol</TableHead>
                  <TableHead className="text-right text-xs sm:text-sm">Qty</TableHead>
                  <TableHead className="text-right text-xs sm:text-sm hidden sm:table-cell">Avg Price</TableHead>
                  <TableHead className="text-right text-xs sm:text-sm">LTP</TableHead>
                  <TableHead className="text-right text-xs sm:text-sm hidden md:table-cell">Value</TableHead>
                  <TableHead className="text-right text-xs sm:text-sm">P&L</TableHead>
                  <TableHead className="text-right text-xs sm:text-sm">Action</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {holdings.map((holding) => (
                  <TableRow key={holding.symbol}>
                    <TableCell className="py-2 sm:py-4">
                      <div>
                        <div className="font-semibold text-xs sm:text-sm">{holding.symbol}</div>
                        <div className="text-[10px] sm:text-xs text-muted-foreground truncate max-w-[100px] sm:max-w-none">{holding.company}</div>
                      </div>
                    </TableCell>
                    <TableCell className="text-right font-mono text-xs sm:text-sm">{holding.quantity}</TableCell>
                    <TableCell className="text-right font-mono text-xs sm:text-sm hidden sm:table-cell">
                      {formatPrice(holding.averageBuyPrice, market)}
                    </TableCell>
                    <TableCell className="text-right font-mono text-xs sm:text-sm">
                      {formatPrice(holding.currentPrice, market)}
                    </TableCell>
                    <TableCell className="text-right font-mono text-xs sm:text-sm hidden md:table-cell">
                      {formatPrice(holding.currentValue, market)}
                    </TableCell>
                    <TableCell className={`text-right font-mono text-xs sm:text-sm ${holding.pnl >= 0 ? 'text-green-500' : 'text-red-500'}`}>
                      <div>{formatPnL(holding.pnl, market)}</div>
                      <div className="text-[10px] sm:text-xs">({holding.pnlPercent >= 0 ? '+' : ''}{holding.pnlPercent.toFixed(2)}%)</div>
                    </TableCell>
                    <TableCell className="text-right">
                      <Link href={`/simulator/${holding.symbol}?exchange=${holding.exchange}`}>
                        <Button variant="outline" size="sm" className="text-[10px] sm:text-xs px-2 sm:px-3 h-7 sm:h-8">
                          Trade
                        </Button>
                      </Link>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {/* Recent Transactions */}
      {transactions.length > 0 && (
        <Card className="border-border/30">
          <CardHeader className="p-4 sm:p-6">
            <CardTitle className="text-base sm:text-lg font-semibold flex items-center gap-2">
              <History className={`h-4 w-4 sm:h-5 sm:w-5 ${market === 'IN' ? 'text-yellow-500' : 'text-blue-500'}`} />
              Recent {market === 'IN' ? 'Indian' : 'US'} Transactions
            </CardTitle>
          </CardHeader>
          <CardContent className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="text-xs sm:text-sm">Date</TableHead>
                  <TableHead className="text-xs sm:text-sm">Symbol</TableHead>
                  <TableHead className="text-xs sm:text-sm">Type</TableHead>
                  <TableHead className="text-right text-xs sm:text-sm">Qty</TableHead>
                  <TableHead className="text-right text-xs sm:text-sm hidden sm:table-cell">Price</TableHead>
                  <TableHead className="text-right text-xs sm:text-sm">Total</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {transactions.map((tx) => (
                  <TableRow key={tx._id}>
                    <TableCell className="text-muted-foreground text-xs sm:text-sm whitespace-nowrap">
                      {new Date(tx.timestamp).toLocaleDateString(getLocaleForMarket(market), {
                        timeZone: getTimezoneForMarket(market),
                        day: '2-digit',
                        month: 'short',
                        hour: '2-digit',
                        minute: '2-digit',
                      })}
                    </TableCell>
                    <TableCell className="font-semibold text-xs sm:text-sm">{tx.symbol}</TableCell>
                    <TableCell>
                      <span className={`px-1.5 sm:px-2 py-0.5 rounded text-[10px] sm:text-xs font-medium ${
                        tx.type === 'BUY' 
                          ? 'bg-green-500/20 text-green-500' 
                          : 'bg-red-500/20 text-red-500'
                      }`}>
                        {tx.type}
                      </span>
                    </TableCell>
                    <TableCell className="text-right font-mono text-xs sm:text-sm">{tx.quantity}</TableCell>
                    <TableCell className="text-right font-mono text-xs sm:text-sm hidden sm:table-cell">
                      {formatPrice(tx.price, market)}
                    </TableCell>
                    <TableCell className="text-right font-mono text-xs sm:text-sm">
                      {formatPrice(tx.totalAmount, market)}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}

      {/* Daily Profit/Loss History */}
      {profitHistory.length > 0 && (
        <Card className="border-border/30">
          <CardHeader className="p-4 sm:p-6">
            <CardTitle className="text-base sm:text-lg font-semibold flex items-center gap-2">
              <Calendar className={`h-4 w-4 sm:h-5 sm:w-5 ${market === 'IN' ? 'text-yellow-500' : 'text-blue-500'}`} />
              Daily P/L History
            </CardTitle>
          </CardHeader>
          <CardContent className="overflow-x-auto p-4 sm:p-6 pt-0">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="text-xs sm:text-sm">Date</TableHead>
                  <TableHead className="text-right text-xs sm:text-sm">Bought</TableHead>
                  <TableHead className="text-right text-xs sm:text-sm">Sold</TableHead>
                  <TableHead className="text-right text-xs sm:text-sm">Net P/L</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {profitHistory.map((day) => (
                  <TableRow key={day.date}>
                    <TableCell className="font-medium text-xs sm:text-sm whitespace-nowrap">
                      {new Date(day.displayDate).toLocaleDateString(getLocaleForMarket(market), {
                        timeZone: getTimezoneForMarket(market),
                        weekday: 'short',
                        day: '2-digit',
                        month: 'short',
                      })}
                    </TableCell>
                    <TableCell className="text-right font-mono text-red-500 text-xs sm:text-sm">
                      {day.buys > 0 ? `-${formatPrice(day.buys, market).slice(1)}` : '-'}
                    </TableCell>
                    <TableCell className="text-right font-mono text-green-500 text-xs sm:text-sm">
                      {day.sells > 0 ? `+${formatPrice(day.sells, market).slice(1)}` : '-'}
                    </TableCell>
                    <TableCell className={`text-right font-mono font-semibold text-xs sm:text-sm ${
                      day.pnl >= 0 ? 'text-green-500' : 'text-red-500'
                    }`}>
                      {formatPnL(day.pnl, market)}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
