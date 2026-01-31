'use client';

import { useState, useEffect, useCallback } from 'react';
import Link from 'next/link';
import { useRouter, useSearchParams } from 'next/navigation';
import { usePageContext } from '@/context/PageContext';
import RealtimeChart from '@/components/simulator/RealtimeChart';
import OrderPanel from '@/components/simulator/OrderPanel';
import { getTransactionHistory, type TransactionHistoryItem } from '@/lib/actions/trading.actions';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { ArrowLeft, History } from 'lucide-react';
import TradingLoader from '@/components/ui/TradingLoader';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

interface TradingTerminalProps {
  readonly symbol: string;
}

// Currency formatting helpers
function isIndianExchange(exchange: string): boolean {
  const exch = (exchange || 'US').toUpperCase();
  return exch === 'BSE' || exch === 'NSE' || exch === 'BO' || exch === 'NS' || exch === 'IN';
}

function formatPrice(price: number, exchange: string): string {
  const isIndian = isIndianExchange(exchange);
  if (isIndian) {
    return `₹${price.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  }
  return `$${price.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

function getLocaleForExchange(exchange: string): string {
  return isIndianExchange(exchange) ? 'en-IN' : 'en-US';
}

function getTimezoneForExchange(exchange: string): string {
  return isIndianExchange(exchange) ? 'Asia/Kolkata' : 'America/New_York';
}

interface StockInfo {
  company: string;
  exchange: string;
  currentPrice: number;
  change: number;
  changePercent: number;
}

export default function TradingTerminal({ symbol }: TradingTerminalProps) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const exchangeFromUrl = searchParams.get('exchange') || 'US';
  const { setExclusivePage, clearExclusivePage } = usePageContext();
  
  const [loading, setLoading] = useState(true);
  const [currentPrice, setCurrentPrice] = useState<number | null>(null);
  const [stockInfo, setStockInfo] = useState<StockInfo | null>(null);
  const [transactions, setTransactions] = useState<TransactionHistoryItem[]>([]);

  // Register as exclusive page to pause background watchlist fetches
  useEffect(() => {
    setExclusivePage('simulator');
    return () => {
      clearExclusivePage();
    };
  }, [setExclusivePage, clearExclusivePage]);

  // Fetch stock info and recent transactions
  useEffect(() => {
    const fetchData = async () => {
      setLoading(true);
      try {
        // Use the quotes/info endpoint for single stock data with exchange
        const response = await fetch(`/api/quotes/info?symbol=${encodeURIComponent(symbol)}&exchange=${encodeURIComponent(exchangeFromUrl)}`);
        if (response.ok) {
          const data = await response.json();
          if (data?.currentPrice) {
            setStockInfo({
              company: data.name || data.shortName || symbol,
              exchange: data.exchange || exchangeFromUrl,
              currentPrice: data.currentPrice || 0,
              change: data.change || 0,
              changePercent: data.percentChange || 0,
            });
            setCurrentPrice(data.currentPrice);
          } else {
            console.error('Invalid quote data:', data);
          }
        } else {
          console.error('Failed to fetch quote:', response.status);
        }

        // Fetch recent transactions for this symbol
        const txResult = await getTransactionHistory(1, 5, symbol);
        if (txResult.success) {
          setTransactions(txResult.transactions);
        }
      } catch (error) {
        console.error('Error fetching stock data:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [symbol, exchangeFromUrl]);

  const refreshTransactions = async () => {
    const txResult = await getTransactionHistory(1, 5, symbol);
    if (txResult.success) {
      setTransactions(txResult.transactions);
    }
  };

  const handlePriceUpdate = useCallback((price: number) => {
    setCurrentPrice(price);
  }, []);

  if (loading && !stockInfo) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <TradingLoader />
      </div>
    );
  }

  return (
    <div className="p-4 sm:p-6 space-y-4 sm:space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div className="flex items-center gap-3 sm:gap-4">
          <Button variant="ghost" size="icon" onClick={() => router.back()} className="h-8 w-8 sm:h-10 sm:w-10">
            <ArrowLeft className="h-4 w-4 sm:h-5 sm:w-5" />
          </Button>
          <div>
            <h1 className="text-xl sm:text-2xl font-bold text-foreground">{symbol}</h1>
            <p className="text-xs sm:text-sm text-muted-foreground">
              {stockInfo?.company || 'Loading...'}
              {stockInfo?.exchange && ` • ${stockInfo.exchange}`}
            </p>
          </div>
        </div>
        <div className="text-left sm:text-right pl-11 sm:pl-0">
          {currentPrice !== null && (
            <>
              <div className="text-xl sm:text-2xl font-bold font-mono">
                {formatPrice(currentPrice, stockInfo?.exchange || exchangeFromUrl)}
              </div>
              {stockInfo && (
                <div className={`text-xs sm:text-sm ${stockInfo.change >= 0 ? 'text-green-500' : 'text-red-500'}`}>
                  {stockInfo.change >= 0 ? '+' : ''}
                  {stockInfo.change.toFixed(2)} ({stockInfo.changePercent >= 0 ? '+' : ''}
                  {stockInfo.changePercent.toFixed(2)}%)
                </div>
              )}
            </>
          )}
        </div>
      </div>

      {/* Main Content - Chart + Order Panel */}
      <div className="grid grid-cols-1 lg:grid-cols-[1fr_350px] gap-4 sm:gap-6">
        {/* Chart Section */}
        <div className="order-2 lg:order-1">
          <RealtimeChart
            symbol={symbol}
            exchange={stockInfo?.exchange || 'US'}
            height={350}
            className="sm:min-h-[400px] lg:min-h-[500px]"
            onPriceUpdate={handlePriceUpdate}
          />
        </div>

        {/* Order Panel */}
        <div className="order-1 lg:order-2">
          <OrderPanel
            symbol={symbol}
            company={stockInfo?.company || symbol}
            exchange={stockInfo?.exchange || 'US'}
            currentPrice={currentPrice}
            onTradeComplete={refreshTransactions}
          />
        </div>
      </div>

      {/* Recent Transactions for this symbol */}
      {transactions.length > 0 && (
        <Card className="border-border/30">
          <CardHeader className="pb-2 sm:pb-4">
            <CardTitle className="text-base sm:text-lg font-semibold flex items-center gap-2">
              <History className="h-4 w-4 sm:h-5 sm:w-5 text-yellow-500" />
              Recent {symbol} Transactions
            </CardTitle>
          </CardHeader>
          <CardContent className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="text-xs sm:text-sm">Date</TableHead>
                  <TableHead className="text-xs sm:text-sm">Type</TableHead>
                  <TableHead className="text-right text-xs sm:text-sm">Qty</TableHead>
                  <TableHead className="text-right text-xs sm:text-sm hidden sm:table-cell">Price</TableHead>
                  <TableHead className="text-right text-xs sm:text-sm">Total</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {transactions.map((tx) => {
                  const txExchange = stockInfo?.exchange || exchangeFromUrl;
                  return (
                    <TableRow key={tx._id}>
                      <TableCell className="text-muted-foreground text-xs sm:text-sm whitespace-nowrap">
                        {new Date(tx.timestamp).toLocaleDateString(getLocaleForExchange(txExchange), {
                          timeZone: getTimezoneForExchange(txExchange),
                          day: '2-digit',
                          month: 'short',
                          hour: '2-digit',
                          minute: '2-digit',
                        })}
                      </TableCell>
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
                        {formatPrice(tx.price, txExchange)}
                      </TableCell>
                      <TableCell className="text-right font-mono text-xs sm:text-sm">
                        {formatPrice(tx.totalAmount, txExchange)}
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}

      {/* Quick Links */}
      <div className="flex flex-wrap items-center gap-2 sm:gap-4 text-xs sm:text-sm">
        <Link href="/simulator" className="text-yellow-500 hover:text-yellow-400">
          ← Back to Portfolio
        </Link>
        <span className="text-muted-foreground hidden sm:inline">•</span>
        <Link href={`/stock/${symbol}`} className="text-muted-foreground hover:text-foreground">
          View Stock Details
        </Link>
        <span className="text-muted-foreground hidden sm:inline">•</span>
        <Link href="/market-scope" className="text-muted-foreground hover:text-foreground">
          Explore Market Scope
        </Link>
      </div>
    </div>
  );
}
