'use server';

import mongoose from 'mongoose';
import { connectToDatabase } from '@/database/mongoose';
import User, { type IUser } from '@/database/models/user.model';
import Portfolio, { type IPortfolio } from '@/database/models/portfolio.model';
import Transaction, { type TransactionType } from '@/database/models/transaction.model';
import { getStockQuoteRealtime } from '@/lib/actions/finnhub.actions';
import { requireCurrentUser } from '@/lib/actions/session.actions';

// ============================================================================
// TYPES
// ============================================================================

export type MarketType = 'IN' | 'US';

export type TradeResult = {
  success: boolean;
  message: string;
  transaction?: {
    id: string;
    symbol: string;
    type: TransactionType;
    quantity: number;
    price: number;
    totalAmount: number;
    balanceAfter: number;
    timestamp: Date;
  };
  error?: string;
};

export type PortfolioHolding = {
  symbol: string;
  company: string;
  exchange: string;
  quantity: number;
  averageBuyPrice: number;
  totalInvested: number;
  currentPrice: number;
  currentValue: number;
  pnl: number;
  pnlPercent: number;
};

export type PortfolioSummaryResult = {
  success: boolean;
  holdings: PortfolioHolding[];
  totalValue: number;
  totalPnL: number;
  totalPnLPercent: number;
  error?: string;
};

export type TransactionHistoryItem = {
  _id: string;
  symbol: string;
  company: string;
  exchange: string;
  type: TransactionType;
  quantity: number;
  price: number;
  totalAmount: number;
  balanceAfter: number;
  timestamp: Date;
};

// ============================================================================
// HELPER FUNCTIONS
// ============================================================================

const DEFAULT_INDIAN_BALANCE = 1000000; // ₹10,00,000
const DEFAULT_US_BALANCE = 100000; // $100,000

// Check if exchange is Indian
function isIndianExchange(exchange: string): boolean {
  const exch = (exchange || 'US').toUpperCase();
  return exch === 'BSE' || exch === 'NSE' || exch === 'BO' || exch === 'NS' || exch === 'IN';
}

// Get market type from exchange
function getMarketFromExchange(exchange: string): MarketType {
  return isIndianExchange(exchange) ? 'IN' : 'US';
}

async function getOrCreateUser(userId: string, email: string): Promise<IUser> {
  await connectToDatabase();
  
  // First try to find by userId (as _id)
  let user = await User.findById(userId);
  
  // If not found, try to find by email
  if (!user) {
    user = await User.findOne({ email });
  }
  
  // If still not found, create new user
  if (!user) {
    user = await User.create({
      _id: userId,
      email,
      indianBalance: DEFAULT_INDIAN_BALANCE,
      usBalance: DEFAULT_US_BALANCE,
    });
  }
  
  // Migration: If user exists but doesn't have separate balances
  if (user.indianBalance === undefined) {
    user.indianBalance = DEFAULT_INDIAN_BALANCE;
    user.usBalance = DEFAULT_US_BALANCE;
    await user.save();
  }
  
  return user;
}

// Get balance for a specific market
function getUserBalanceForMarket(user: IUser, market: MarketType): number {
  return market === 'IN' ? (user.indianBalance ?? DEFAULT_INDIAN_BALANCE) : (user.usBalance ?? DEFAULT_US_BALANCE);
}

// Set balance for a specific market
async function setUserBalanceForMarket(
  userId: string,
  market: MarketType,
  balance: number,
  session?: mongoose.ClientSession
): Promise<void> {
  const field = market === 'IN' ? 'indianBalance' : 'usBalance';
  await User.updateOne(
    { _id: userId },
    { $set: { [field]: balance } },
    session ? { session } : {}
  );
}

async function getCurrentPrice(symbol: string): Promise<number> {
  try {
    const quote = await getStockQuoteRealtime({ symbol });
    if (quote && typeof quote.currentPrice === 'number' && quote.currentPrice > 0) {
      return quote.currentPrice;
    }
    throw new Error(`Unable to fetch price for ${symbol}`);
  } catch (error) {
    console.error(`Error fetching price for ${symbol}:`, error);
    throw new Error(`Unable to fetch current price for ${symbol}`);
  }
}

// ============================================================================
// EXECUTE TRADE
// ============================================================================

export async function executeTrade(args: {
  symbol: string;
  company: string;
  exchange: string;
  type: TransactionType;
  quantity: number;
  price: number;
}): Promise<TradeResult> {
  const { symbol, company, exchange, type, quantity, price: currentPrice } = args;

  // Get current user from session
  let userId: string;
  let userEmail: string;
  try {
    const sessionUser = await requireCurrentUser();
    userId = sessionUser.userId;
    userEmail = sessionUser.email;
  } catch {
    return { success: false, message: 'Please sign in to trade', error: 'UNAUTHORIZED' };
  }

  // Validate inputs
  if (!symbol || typeof symbol !== 'string') {
    return { success: false, message: 'Invalid symbol', error: 'INVALID_SYMBOL' };
  }

  if (quantity <= 0 || !Number.isInteger(quantity)) {
    return { success: false, message: 'Quantity must be a positive integer', error: 'INVALID_QUANTITY' };
  }

  if (currentPrice <= 0 || !Number.isFinite(currentPrice)) {
    return { success: false, message: 'Invalid price', error: 'INVALID_PRICE' };
  }

  const totalAmount = quantity * currentPrice;
  const symbolUpper = symbol.toUpperCase().trim();

  await connectToDatabase();

  // Use a session for atomic operations
  const session = await mongoose.startSession();
  
  try {
    session.startTransaction();

    // Get or create user
    let user = await User.findById(userId).session(session);
    
    // If not found by ID, try by email
    if (!user) {
      user = await User.findOne({ email: userEmail }).session(session);
    }
    
    if (!user) {
      user = new User({
        _id: userId,
        email: userEmail,
        indianBalance: DEFAULT_INDIAN_BALANCE,
        usBalance: DEFAULT_US_BALANCE,
      });
      await user.save({ session });
    }

    // Determine market type from exchange
    const market = getMarketFromExchange(exchange);
    const userBalance = getUserBalanceForMarket(user, market);
    const currencySymbol = market === 'IN' ? '₹' : '$';

    if (type === 'BUY') {
      // Check sufficient funds
      if (userBalance < totalAmount) {
        await session.abortTransaction();
        return {
          success: false,
          message: `Insufficient funds. Required: ${currencySymbol}${totalAmount.toFixed(2)}, Available: ${currencySymbol}${userBalance.toFixed(2)}`,
          error: 'INSUFFICIENT_FUNDS',
        };
      }

      // Deduct balance from the appropriate market
      const newBalance = userBalance - totalAmount;
      if (market === 'IN') {
        user.indianBalance = newBalance;
      } else {
        user.usBalance = newBalance;
      }
      await user.save({ session });

      // Update or create portfolio holding
      const existingHolding = await Portfolio.findOne({ userId, symbol: symbolUpper }).session(session);

      if (existingHolding) {
        // Update existing holding with weighted average price
        const newTotalQuantity = existingHolding.quantity + quantity;
        const newTotalInvested = existingHolding.totalInvested + totalAmount;
        const newAveragePrice = newTotalInvested / newTotalQuantity;

        existingHolding.quantity = newTotalQuantity;
        existingHolding.totalInvested = newTotalInvested;
        existingHolding.averageBuyPrice = newAveragePrice;
        await existingHolding.save({ session });
      } else {
        // Create new holding
        await Portfolio.create(
          [
            {
              userId,
              symbol: symbolUpper,
              company,
              exchange,
              quantity,
              averageBuyPrice: currentPrice,
              totalInvested: totalAmount,
            },
          ],
          { session }
        );
      }
    } else {
      // SELL
      const existingHolding = await Portfolio.findOne({ userId, symbol: symbolUpper }).session(session);

      if (!existingHolding) {
        await session.abortTransaction();
        return {
          success: false,
          message: `You don't own any shares of ${symbolUpper}`,
          error: 'NO_HOLDINGS',
        };
      }

      if (existingHolding.quantity < quantity) {
        await session.abortTransaction();
        return {
          success: false,
          message: `Insufficient shares. You own ${existingHolding.quantity} shares of ${symbolUpper}`,
          error: 'INSUFFICIENT_SHARES',
        };
      }

      // Add sale proceeds to the appropriate market balance
      const newBalance = userBalance + totalAmount;
      if (market === 'IN') {
        user.indianBalance = newBalance;
      } else {
        user.usBalance = newBalance;
      }
      await user.save({ session });

      // Update portfolio
      if (existingHolding.quantity === quantity) {
        // Sell all shares - remove the holding
        await Portfolio.deleteOne({ _id: existingHolding._id }).session(session);
      } else {
        // Partial sell - reduce quantity and invested amount proportionally
        const sellRatio = quantity / existingHolding.quantity;
        existingHolding.quantity -= quantity;
        existingHolding.totalInvested -= existingHolding.totalInvested * sellRatio;
        await existingHolding.save({ session });
      }
    }

    // Create transaction record
    const newBalance = market === 'IN' ? user.indianBalance : user.usBalance;
    const transaction = await Transaction.create(
      [
        {
          userId,
          symbol: symbolUpper,
          company,
          exchange,
          type,
          quantity,
          price: currentPrice,
          totalAmount,
          balanceAfter: newBalance,
          timestamp: new Date(),
        },
      ],
      { session }
    );

    await session.commitTransaction();

    return {
      success: true,
      message: `Successfully ${type === 'BUY' ? 'bought' : 'sold'} ${quantity} shares of ${symbolUpper} at ${currencySymbol}${currentPrice.toFixed(2)}`,
      transaction: {
        id: transaction[0]._id.toString(),
        symbol: symbolUpper,
        type,
        quantity,
        price: currentPrice,
        totalAmount,
        balanceAfter: newBalance,
        timestamp: transaction[0].timestamp,
      },
    };
  } catch (error) {
    await session.abortTransaction();
    console.error('Trade execution error:', error);
    return {
      success: false,
      message: 'An error occurred while executing the trade',
      error: 'EXECUTION_ERROR',
    };
  } finally {
    session.endSession();
  }
}

// ============================================================================
// GET PORTFOLIO SUMMARY
// ============================================================================

export async function getPortfolioSummary(market?: MarketType): Promise<PortfolioSummaryResult> {
  // Get current user from session
  let userId: string;
  try {
    const user = await requireCurrentUser();
    userId = user.userId;
  } catch {
    return {
      success: false,
      holdings: [],
      totalValue: 0,
      totalPnL: 0,
      totalPnLPercent: 0,
      error: 'UNAUTHORIZED',
    };
  }

  await connectToDatabase();

  // Build query - filter by market if specified
  const query: Record<string, unknown> = { userId };
  if (market) {
    if (market === 'IN') {
      // Indian exchanges
      query.exchange = { $in: ['BSE', 'NSE', 'BO', 'NS', 'IN'] };
    } else {
      // US exchanges (everything not Indian)
      query.exchange = { $nin: ['BSE', 'NSE', 'BO', 'NS', 'IN'] };
    }
  }

  // Get holdings filtered by market
  const portfolioItems = await Portfolio.find(query).lean();

  if (portfolioItems.length === 0) {
    return {
      success: true,
      holdings: [],
      totalValue: 0,
      totalPnL: 0,
      totalPnLPercent: 0,
    };
  }

  // Fetch current prices for all holdings
  const holdings: PortfolioHolding[] = [];
  let totalInvested = 0;
  let currentPortfolioValue = 0;

  for (const item of portfolioItems) {
    try {
      const currentPrice = await getCurrentPrice(item.symbol);
      const currentValue = item.quantity * currentPrice;
      const pnl = currentValue - item.totalInvested;
      const pnlPercent = item.totalInvested > 0 ? (pnl / item.totalInvested) * 100 : 0;

      holdings.push({
        symbol: item.symbol,
        company: item.company,
        exchange: item.exchange,
        quantity: item.quantity,
        averageBuyPrice: item.averageBuyPrice,
        totalInvested: item.totalInvested,
        currentPrice,
        currentValue,
        pnl,
        pnlPercent,
      });

      totalInvested += item.totalInvested;
      currentPortfolioValue += currentValue;
    } catch (error) {
      console.error(`Error fetching price for ${item.symbol}:`, error);
      // Use average buy price as fallback
      const currentValue = item.quantity * item.averageBuyPrice;
      holdings.push({
        symbol: item.symbol,
        company: item.company,
        exchange: item.exchange,
        quantity: item.quantity,
        averageBuyPrice: item.averageBuyPrice,
        totalInvested: item.totalInvested,
        currentPrice: item.averageBuyPrice,
        currentValue,
        pnl: 0,
        pnlPercent: 0,
      });
      totalInvested += item.totalInvested;
      currentPortfolioValue += currentValue;
    }
  }

  const totalPnL = currentPortfolioValue - totalInvested;
  const totalPnLPercent = totalInvested > 0 ? (totalPnL / totalInvested) * 100 : 0;

  return {
    success: true,
    holdings,
    totalValue: currentPortfolioValue,
    totalPnL,
    totalPnLPercent,
  };
}

// ============================================================================
// GET USER BALANCE
// ============================================================================

export async function getUserBalance(market: MarketType = 'IN'): Promise<{
  success: boolean;
  balance: number;
  indianBalance: number;
  usBalance: number;
  error?: string;
}> {
  // Get current user from session
  let userId: string;
  let userEmail: string;
  try {
    const sessionUser = await requireCurrentUser();
    userId = sessionUser.userId;
    userEmail = sessionUser.email;
  } catch {
    return {
      success: false,
      balance: market === 'IN' ? DEFAULT_INDIAN_BALANCE : DEFAULT_US_BALANCE,
      indianBalance: DEFAULT_INDIAN_BALANCE,
      usBalance: DEFAULT_US_BALANCE,
      error: 'UNAUTHORIZED',
    };
  }

  await connectToDatabase();
  const user = await getOrCreateUser(userId, userEmail);

  return {
    success: true,
    balance: market === 'IN' ? (user.indianBalance ?? DEFAULT_INDIAN_BALANCE) : (user.usBalance ?? DEFAULT_US_BALANCE),
    indianBalance: user.indianBalance ?? DEFAULT_INDIAN_BALANCE,
    usBalance: user.usBalance ?? DEFAULT_US_BALANCE,
  };
}

// ============================================================================
// GET PORTFOLIO HOLDINGS (SIMPLE)
// ============================================================================

export async function getPortfolioHoldings(): Promise<IPortfolio[]> {
  // Get current user from session
  let userId: string;
  try {
    const user = await requireCurrentUser();
    userId = user.userId;
  } catch {
    return [];
  }

  await connectToDatabase();
  return Portfolio.find({ userId }).lean();
}

// ============================================================================
// GET HOLDING FOR SYMBOL
// ============================================================================

export async function getHoldingForSymbol(
  symbol: string
): Promise<{
  success: boolean;
  holding: { quantity: number; averageBuyPrice: number } | null;
  error?: string;
}> {
  if (!symbol) {
    return { success: false, holding: null, error: 'INVALID_SYMBOL' };
  }

  // Get current user from session
  let userId: string;
  try {
    const user = await requireCurrentUser();
    userId = user.userId;
  } catch {
    return { success: false, holding: null, error: 'UNAUTHORIZED' };
  }

  await connectToDatabase();
  const holding = await Portfolio.findOne({ userId, symbol: symbol.toUpperCase() }).lean();

  if (!holding) {
    return { success: true, holding: null };
  }

  return {
    success: true,
    holding: {
      quantity: holding.quantity,
      averageBuyPrice: holding.averageBuyPrice,
    },
  };
}

// ============================================================================
// GET TRANSACTION HISTORY
// ============================================================================

export async function getTransactionHistory(
  page: number = 1,
  limit: number = 10,
  symbol?: string,
  market?: MarketType
): Promise<{
  success: boolean;
  transactions: TransactionHistoryItem[];
  error?: string;
}> {
  // Get current user from session
  let userId: string;
  try {
    const user = await requireCurrentUser();
    userId = user.userId;
  } catch {
    return { success: false, transactions: [], error: 'UNAUTHORIZED' };
  }

  await connectToDatabase();

  const query: Record<string, unknown> = { userId };
  if (symbol) {
    query.symbol = symbol.toUpperCase();
  }
  
  // Filter by market if specified
  if (market) {
    if (market === 'IN') {
      query.exchange = { $in: ['BSE', 'NSE', 'BO', 'NS', 'IN'] };
    } else {
      query.exchange = { $nin: ['BSE', 'NSE', 'BO', 'NS', 'IN'] };
    }
  }

  const skip = (page - 1) * limit;

  const transactions = await Transaction.find(query)
    .sort({ timestamp: -1 })
    .skip(skip)
    .limit(limit)
    .lean();

  return {
    success: true,
    transactions: transactions.map((t) => ({
      _id: t._id.toString(),
      symbol: t.symbol,
      company: t.company,
      exchange: t.exchange || 'US',
      type: t.type,
      quantity: t.quantity,
      price: t.price,
      totalAmount: t.totalAmount,
      balanceAfter: t.balanceAfter,
      timestamp: t.timestamp,
    })),
  };
}

// ============================================================================
// RESET PORTFOLIO (FOR TESTING / USER REQUEST)
// ============================================================================

export async function resetPortfolio(market?: MarketType): Promise<{ success: boolean; message: string }> {
  // Get current user from session
  let userId: string;
  try {
    const user = await requireCurrentUser();
    userId = user.userId;
  } catch {
    return { success: false, message: 'Please sign in to reset portfolio' };
  }

  await connectToDatabase();

  const session = await mongoose.startSession();

  try {
    session.startTransaction();

    // Build query for filtering by market
    const portfolioQuery: Record<string, unknown> = { userId };
    const transactionQuery: Record<string, unknown> = { userId };
    
    if (market) {
      if (market === 'IN') {
        portfolioQuery.exchange = { $in: ['BSE', 'NSE', 'BO', 'NS', 'IN'] };
        transactionQuery.exchange = { $in: ['BSE', 'NSE', 'BO', 'NS', 'IN'] };
      } else {
        portfolioQuery.exchange = { $nin: ['BSE', 'NSE', 'BO', 'NS', 'IN'] };
        transactionQuery.exchange = { $nin: ['BSE', 'NSE', 'BO', 'NS', 'IN'] };
      }
    }

    // Reset user balance for the specific market
    const updateFields: Record<string, unknown> = {};
    if (!market || market === 'IN') {
      updateFields.indianBalance = DEFAULT_INDIAN_BALANCE;
    }
    if (!market || market === 'US') {
      updateFields.usBalance = DEFAULT_US_BALANCE;
    }
    
    await User.updateOne(
      { _id: userId },
      { $set: updateFields },
      { upsert: true, session }
    );

    // Delete holdings for the specific market
    await Portfolio.deleteMany(portfolioQuery).session(session);

    // Delete transactions for the specific market
    await Transaction.deleteMany(transactionQuery).session(session);

    await session.commitTransaction();

    const marketLabel = market === 'IN' ? 'Indian' : market === 'US' ? 'American' : 'All';
    const balanceMsg = market === 'IN' 
      ? `₹${DEFAULT_INDIAN_BALANCE.toLocaleString('en-IN')}`
      : market === 'US'
      ? `$${DEFAULT_US_BALANCE.toLocaleString('en-US')}`
      : `₹${DEFAULT_INDIAN_BALANCE.toLocaleString('en-IN')} (Indian) & $${DEFAULT_US_BALANCE.toLocaleString('en-US')} (US)`;

    return {
      success: true,
      message: `${marketLabel} portfolio reset successfully. Balance restored to ${balanceMsg}`,
    };
  } catch (error) {
    await session.abortTransaction();
    console.error('Portfolio reset error:', error);
    return { success: false, message: 'An error occurred while resetting the portfolio' };
  } finally {
    session.endSession();
  }
}

// ============================================================================
// GET HISTORICAL CANDLES FOR CHART
// ============================================================================

/**
 * Convert symbol to Yahoo Finance format based on exchange
 * Indian stocks need .NS (NSE) or .BO (BSE) suffix
 */
function toYahooSymbol(symbol: string, exchange?: string): string {
  const sym = symbol.toUpperCase().trim();
  const exch = (exchange || 'US').toUpperCase().trim();
  
  // If already has a suffix, return as-is
  if (sym.includes('.')) return sym;
  
  // Indian exchanges
  if (exch === 'BSE' || exch === 'BO') {
    return `${sym}.BO`;
  }
  if (exch === 'NSE' || exch === 'NS' || exch === 'IN') {
    return `${sym}.NS`;
  }
  
  // US stocks don't need suffix
  return sym;
}

/**
 * Check if a timestamp falls within market trading hours
 * Indian Market: 9:00 AM - 4:00 PM IST (includes pre-open and closing session)
 * US Market: 9:30 AM - 4:00 PM EST
 */
function isWithinMarketHours(timestamp: number, exchange?: string): boolean {
  const date = new Date(timestamp * 1000);
  const isIndian = isIndianExchange(exchange || '');
  
  if (isIndian) {
    // Convert to IST and check market hours
    const istFormatter = new Intl.DateTimeFormat('en-US', {
      timeZone: 'Asia/Kolkata',
      hour: 'numeric',
      minute: 'numeric',
      hour12: false,
      weekday: 'short',
    });
    const parts = istFormatter.formatToParts(date);
    const hour = Number.parseInt(parts.find(p => p.type === 'hour')?.value ?? '0', 10);
    const minute = Number.parseInt(parts.find(p => p.type === 'minute')?.value ?? '0', 10);
    const weekday = parts.find(p => p.type === 'weekday')?.value ?? '';
    
    // Skip weekends
    if (weekday === 'Sat' || weekday === 'Sun') return false;
    
    const timeInMinutes = hour * 60 + minute;
    // 9:00 AM = 540 minutes, 4:00 PM = 960 minutes
    return timeInMinutes >= 540 && timeInMinutes <= 960;
  } else {
    // US Market - Convert to EST and check market hours
    const estFormatter = new Intl.DateTimeFormat('en-US', {
      timeZone: 'America/New_York',
      hour: 'numeric',
      minute: 'numeric',
      hour12: false,
      weekday: 'short',
    });
    const parts = estFormatter.formatToParts(date);
    const hour = Number.parseInt(parts.find(p => p.type === 'hour')?.value ?? '0', 10);
    const minute = Number.parseInt(parts.find(p => p.type === 'minute')?.value ?? '0', 10);
    const weekday = parts.find(p => p.type === 'weekday')?.value ?? '';
    
    // Skip weekends
    if (weekday === 'Sat' || weekday === 'Sun') return false;
    
    const timeInMinutes = hour * 60 + minute;
    // 9:30 AM = 570 minutes, 4:00 PM = 960 minutes
    return timeInMinutes >= 570 && timeInMinutes <= 960;
  }
}

/**
 * Check if market is currently open for the given exchange
 */
function isMarketCurrentlyOpen(exchange?: string): boolean {
  const now = new Date();
  const isIndian = isIndianExchange(exchange || '');
  
  if (isIndian) {
    const istFormatter = new Intl.DateTimeFormat('en-US', {
      timeZone: 'Asia/Kolkata',
      hour: 'numeric',
      minute: 'numeric',
      hour12: false,
      weekday: 'short',
    });
    const parts = istFormatter.formatToParts(now);
    const hour = Number.parseInt(parts.find(p => p.type === 'hour')?.value ?? '0', 10);
    const minute = Number.parseInt(parts.find(p => p.type === 'minute')?.value ?? '0', 10);
    const weekday = parts.find(p => p.type === 'weekday')?.value ?? '';
    
    if (weekday === 'Sat' || weekday === 'Sun') return false;
    
    const timeInMinutes = hour * 60 + minute;
    return timeInMinutes >= 540 && timeInMinutes <= 960; // 9:00 AM - 4:00 PM IST
  } else {
    const estFormatter = new Intl.DateTimeFormat('en-US', {
      timeZone: 'America/New_York',
      hour: 'numeric',
      minute: 'numeric',
      hour12: false,
      weekday: 'short',
    });
    const parts = estFormatter.formatToParts(now);
    const hour = Number.parseInt(parts.find(p => p.type === 'hour')?.value ?? '0', 10);
    const minute = Number.parseInt(parts.find(p => p.type === 'minute')?.value ?? '0', 10);
    const weekday = parts.find(p => p.type === 'weekday')?.value ?? '';
    
    if (weekday === 'Sat' || weekday === 'Sun') return false;
    
    const timeInMinutes = hour * 60 + minute;
    return timeInMinutes >= 570 && timeInMinutes <= 960; // 9:30 AM - 4:00 PM EST
  }
}

export async function getHistoricalCandles(
  symbol: string,
  interval: '1m' | '5m' | '15m' | '1h' | '1d' = '5m',
  range: '1d' | '5d' | '1mo' | '3mo' = '1d',
  exchange?: string
): Promise<{
  candles: Array<{
    time: number;
    open: number;
    high: number;
    low: number;
    close: number;
    volume: number;
  }>;
  error?: string;
}> {
  // Convert to Yahoo Finance symbol format
  const yahooSymbol = toYahooSymbol(symbol, exchange);
  
  try {
    const YahooFinance = (await import('yahoo-finance2')).default;

    const yahooFinance = new YahooFinance({
      suppressNotices: ['yahooSurvey'],
      validation: { logErrors: false },
    });

    const period2 = new Date();
    let period1: Date;
    
    // When market is closed and requesting 1d range, extend to 5d to ensure we get last trading day data
    const marketOpen = isMarketCurrentlyOpen(exchange);
    const effectiveRange = (!marketOpen && range === '1d') ? '5d' : range;

    switch (effectiveRange) {
      case '1d':
        period1 = new Date(period2.getTime() - 1 * 24 * 60 * 60 * 1000);
        break;
      case '5d':
        period1 = new Date(period2.getTime() - 5 * 24 * 60 * 60 * 1000);
        break;
      case '1mo':
        period1 = new Date(period2.getTime() - 30 * 24 * 60 * 60 * 1000);
        break;
      case '3mo':
        period1 = new Date(period2.getTime() - 90 * 24 * 60 * 60 * 1000);
        break;
      default:
        period1 = new Date(period2.getTime() - 1 * 24 * 60 * 60 * 1000);
    }

    const chart = (await yahooFinance.chart(yahooSymbol, {
      period1,
      period2,
      interval,
      return: 'object',
    })) as unknown as {
      timestamp?: number[];
      indicators?: {
        quote?: Array<{
          open: Array<number | null>;
          high: Array<number | null>;
          low: Array<number | null>;
          close: Array<number | null>;
          volume: Array<number | null>;
        }>;
      };
    };

    const timestamps = Array.isArray(chart?.timestamp) ? chart.timestamp : [];
    const quote0 = Array.isArray(chart?.indicators?.quote) ? chart.indicators.quote[0] : undefined;
    const opens = quote0?.open ?? [];
    const highs = quote0?.high ?? [];
    const lows = quote0?.low ?? [];
    const closes = quote0?.close ?? [];
    const volumes = quote0?.volume ?? [];

    const candles: Array<{
      time: number;
      open: number;
      high: number;
      low: number;
      close: number;
      volume: number;
    }> = [];

    // For daily candles, don't filter by market hours (each candle represents a full day)
    const shouldFilterMarketHours = interval !== '1d';

    for (let i = 0; i < timestamps.length; i++) {
      const ts = timestamps[i];
      const open = opens[i];
      const high = highs[i];
      const low = lows[i];
      const close = closes[i];
      const volume = volumes[i];

      if (
        typeof ts !== 'number' ||
        !Number.isFinite(ts) ||
        typeof open !== 'number' ||
        !Number.isFinite(open) ||
        typeof high !== 'number' ||
        !Number.isFinite(high) ||
        typeof low !== 'number' ||
        !Number.isFinite(low) ||
        typeof close !== 'number' ||
        !Number.isFinite(close)
      ) {
        continue;
      }

      // Filter out candles outside market hours (for intraday intervals)
      if (shouldFilterMarketHours && !isWithinMarketHours(ts, exchange)) {
        continue;
      }

      candles.push({
        time: ts,
        open,
        high,
        low,
        close,
        volume: typeof volume === 'number' && Number.isFinite(volume) ? volume : 0,
      });
    }

    // If market is closed and we extended the range, return only the last trading day's data
    if (!marketOpen && range === '1d' && candles.length > 0 && interval !== '1d') {
      // Find the last trading day timestamp
      const lastCandle = candles.at(-1)!;
      const lastCandleDate = new Date(lastCandle.time * 1000);
      const isIndian = isIndianExchange(exchange || '');
      const timezone = isIndian ? 'Asia/Kolkata' : 'America/New_York';
      
      // Get the date part of the last candle in the appropriate timezone
      const formatter = new Intl.DateTimeFormat('en-CA', {
        timeZone: timezone,
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
      });
      const lastDateStr = formatter.format(lastCandleDate);
      
      // Filter to only include candles from the last trading day
      const filteredCandles = candles.filter(c => {
        const candleDate = new Date(c.time * 1000);
        const candleDateStr = formatter.format(candleDate);
        return candleDateStr === lastDateStr;
      });
      
      return { candles: filteredCandles.length > 0 ? filteredCandles : candles };
    }

    return { candles };
  } catch (error) {
    console.error(`Error fetching candles for ${symbol} (Yahoo: ${toYahooSymbol(symbol, exchange)}):`, error);
    return { candles: [], error: `Failed to fetch data for ${symbol}` };
  }
}
