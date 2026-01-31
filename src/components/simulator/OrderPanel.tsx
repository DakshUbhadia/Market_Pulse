'use client';

import { useState, useEffect, useCallback } from 'react';
import { executeTrade, getUserBalance, getHoldingForSymbol, type MarketType } from '@/lib/actions/trading.actions';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Loader2, TrendingUp, TrendingDown, AlertCircle } from 'lucide-react';
import { toast } from 'sonner';

interface OrderPanelProps {
  readonly symbol: string;
  readonly company: string;
  readonly exchange: string;
  readonly currentPrice: number | null;
  readonly onTradeComplete?: () => void;
}

// Currency formatting helpers
function isIndianExchange(exch: string): boolean {
  const e = (exch || 'US').toUpperCase();
  return e === 'BSE' || e === 'NSE' || e === 'BO' || e === 'NS' || e === 'IN';
}

function getMarketFromExchange(exchange: string): MarketType {
  return isIndianExchange(exchange) ? 'IN' : 'US';
}

function formatPrice(price: number, exch: string): string {
  const isIndian = isIndianExchange(exch);
  if (isIndian) {
    return `₹${price.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  }
  return `$${price.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

function getCurrencySymbol(exch: string): string {
  return isIndianExchange(exch) ? '₹' : '$';
}

export default function OrderPanel({
  symbol,
  company,
  exchange,
  currentPrice,
  onTradeComplete,
}: OrderPanelProps) {
  const [tab, setTab] = useState<'BUY' | 'SELL'>('BUY');
  const [quantity, setQuantity] = useState<string>('');
  const [loading, setLoading] = useState(false);
  const [balance, setBalance] = useState<number>(0);
  const [holding, setHolding] = useState<{ quantity: number; averageBuyPrice: number } | null>(null);
  const [fetchingData, setFetchingData] = useState(true);

  const qty = Number.parseInt(quantity, 10) || 0;
  const price = currentPrice ?? 0;
  const orderValue = qty * price;
  const market = getMarketFromExchange(exchange);

  // Shared data fetching logic
  const fetchUserData = useCallback(async () => {
    try {
      const [balanceResult, holdingResult] = await Promise.all([
        getUserBalance(market),
        getHoldingForSymbol(symbol),
      ]);

      if (balanceResult.success) {
        // Use market-specific balance
        const marketBalance = market === 'IN' ? balanceResult.indianBalance : balanceResult.usBalance;
        setBalance(marketBalance);
      }

      if (holdingResult.success && holdingResult.holding) {
        setHolding(holdingResult.holding);
      } else {
        setHolding(null);
      }
    } catch (error) {
      console.error('Error fetching user data:', error);
    }
  }, [symbol, market]);

  // Initial data fetch
  useEffect(() => {
    const initFetch = async () => {
      setFetchingData(true);
      await fetchUserData();
      setFetchingData(false);
    };
    initFetch();
  }, [fetchUserData]);

  const handleTrade = async () => {
    if (!currentPrice || qty <= 0) return;

    setLoading(true);
    try {
      const result = await executeTrade({
        symbol,
        company,
        exchange,
        type: tab,
        quantity: qty,
        price: currentPrice,
      });

      if (result.success) {
        const action = tab === 'BUY' ? 'bought' : 'sold';
        
        // For SELL orders, calculate and show P/L
        if (tab === 'SELL' && holding) {
          const tradePnL = (currentPrice - holding.averageBuyPrice) * qty;
          const pnlPercent = ((currentPrice - holding.averageBuyPrice) / holding.averageBuyPrice) * 100;
          const isProfit = tradePnL >= 0;
          const pnlText = `${isProfit ? '+' : ''}${formatPrice(tradePnL, exchange)} (${isProfit ? '+' : ''}${pnlPercent.toFixed(2)}%)`;
          
          if (isProfit) {
            toast.success(`🎉 Sold ${qty} ${symbol} at profit!`, {
              description: `P/L: ${pnlText}`,
              duration: 6000,
            });
          } else {
            toast.error(`📉 Sold ${qty} ${symbol} at loss`, {
              description: `P/L: ${pnlText}`,
              duration: 6000,
            });
          }
        } else {
          toast.success(`Successfully ${action} ${qty} shares of ${symbol}`, {
            description: `Order value: ${formatPrice(orderValue, exchange)}`,
          });
        }
        
        setQuantity('');
        await fetchUserData();
        onTradeComplete?.();
      } else {
        toast.error('Trade failed', { description: result.error });
      }
    } catch (error) {
      console.error('Trade error:', error);
      toast.error('An error occurred while executing the trade');
    } finally {
      setLoading(false);
    }
  };

  const canBuy = qty > 0 && price > 0 && orderValue <= balance;
  const canSell = qty > 0 && price > 0 && holding !== null && qty <= holding.quantity;
  const sellPnL = holding && currentPrice ? (currentPrice - holding.averageBuyPrice) * qty : 0;

  const getBuyButtonText = () => (qty > 0 ? `Buy ${qty} ${symbol}` : `Buy ${symbol}`);
  const getSellButtonText = () => (qty > 0 ? `Sell ${qty} ${symbol}` : `Sell ${symbol}`);

  return (
    <Card className="border-border/30 bg-card/50 backdrop-blur-sm">
      <CardHeader className="pb-3">
        <CardTitle className="text-lg font-semibold flex items-center gap-2">
          <span>Order Entry</span>
          {currentPrice !== null && (
            <span className="text-sm font-mono text-muted-foreground">
              @ {formatPrice(currentPrice, exchange)}
            </span>
          )}
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <Tabs value={tab} onValueChange={(v) => setTab(v as 'BUY' | 'SELL')}>
          <TabsList className="w-full grid grid-cols-2">
            <TabsTrigger
              value="BUY"
              className="data-[state=active]:bg-green-500/20 data-[state=active]:text-green-500"
            >
              <TrendingUp className="h-4 w-4 mr-2" />
              Buy
            </TabsTrigger>
            <TabsTrigger
              value="SELL"
              className="data-[state=active]:bg-red-500/20 data-[state=active]:text-red-500"
            >
              <TrendingDown className="h-4 w-4 mr-2" />
              Sell
            </TabsTrigger>
          </TabsList>

          <TabsContent value="BUY" className="mt-4 space-y-4">
            <div className="space-y-2">
              <span className="text-sm font-medium text-muted-foreground">Quantity</span>
              <Input
                type="number"
                min="1"
                step="1"
                value={quantity}
                onChange={(e) => setQuantity(e.target.value)}
                placeholder="Enter quantity"
                className="font-mono"
                aria-label="Quantity to buy"
              />
            </div>

            <div className="space-y-2 p-3 rounded-lg bg-muted/30 border border-border/30">
              <div className="flex justify-between text-sm">
                <span className="text-muted-foreground">Order Value</span>
                <span className="font-mono font-medium">
                  {formatPrice(orderValue, exchange)}
                </span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-muted-foreground">Available Cash</span>
                <span className={`font-mono font-medium ${orderValue > balance ? 'text-red-500' : 'text-green-500'}`}>
                  {formatPrice(balance, exchange)}
                </span>
              </div>
              {orderValue > balance && (
                <div className="flex items-center gap-2 text-xs text-red-500 mt-2">
                  <AlertCircle className="h-3 w-3" />
                  <span>Insufficient funds</span>
                </div>
              )}
            </div>

            <Button
              onClick={handleTrade}
              disabled={!canBuy || loading || fetchingData}
              className="w-full bg-green-600 hover:bg-green-700 text-white"
            >
              {loading ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Processing...
                </>
              ) : (
                getBuyButtonText()
              )}
            </Button>
          </TabsContent>

          <TabsContent value="SELL" className="mt-4 space-y-4">
            {holding ? (
              <div className="p-3 rounded-lg bg-muted/30 border border-border/30 space-y-1">
                <div className="flex justify-between text-sm">
                  <span className="text-muted-foreground">Your Holdings</span>
                  <span className="font-mono font-medium">{holding.quantity} shares</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-muted-foreground">Avg. Buy Price</span>
                  <span className="font-mono">
                    {formatPrice(holding.averageBuyPrice, exchange)}
                  </span>
                </div>
              </div>
            ) : (
              <div className="p-3 rounded-lg bg-muted/30 border border-border/30 text-center text-sm text-muted-foreground">
                You don&apos;t own any {symbol} shares
              </div>
            )}

            <div className="space-y-2">
              <span className="text-sm font-medium text-muted-foreground">Quantity</span>
              <Input
                type="number"
                min="1"
                max={holding?.quantity || 0}
                step="1"
                value={quantity}
                onChange={(e) => setQuantity(e.target.value)}
                placeholder="Enter quantity"
                className="font-mono"
                disabled={!holding}
                aria-label="Quantity to sell"
              />
              {holding && (
                <button
                  onClick={() => setQuantity(holding.quantity.toString())}
                  className="text-xs text-yellow-500 hover:text-yellow-400"
                  type="button"
                >
                  Sell All ({holding.quantity} shares)
                </button>
              )}
            </div>

            {holding && qty > 0 && (
              <div className="space-y-2 p-3 rounded-lg bg-muted/30 border border-border/30">
                <div className="flex justify-between text-sm">
                  <span className="text-muted-foreground">Order Value</span>
                  <span className="font-mono font-medium">
                    {formatPrice(orderValue, exchange)}
                  </span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-muted-foreground">Est. P&L</span>
                  <span className={`font-mono font-medium ${sellPnL >= 0 ? 'text-green-500' : 'text-red-500'}`}>
                    {sellPnL >= 0 ? '+' : ''}{getCurrencySymbol(exchange)}{Math.abs(sellPnL).toLocaleString(isIndianExchange(exchange) ? 'en-IN' : 'en-US', { maximumFractionDigits: 2 })}
                  </span>
                </div>
                {qty > (holding?.quantity || 0) && (
                  <div className="flex items-center gap-2 text-xs text-red-500 mt-2">
                    <AlertCircle className="h-3 w-3" />
                    <span>Exceeds available holdings</span>
                  </div>
                )}
              </div>
            )}

            <Button
              onClick={handleTrade}
              disabled={!canSell || loading || fetchingData}
              className="w-full bg-red-600 hover:bg-red-700 text-white"
            >
              {loading ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Processing...
                </>
              ) : (
                getSellButtonText()
              )}
            </Button>
          </TabsContent>
        </Tabs>
      </CardContent>
    </Card>
  );
}
