'use server';

import { connectToDatabase } from "@/database/mongoose";
import Watchlist from "@/database/models/watchlist.model";
import { requireCurrentUser } from "@/lib/actions/session.actions";

interface BetterAuthUserDoc {
  id?: string;
  _id?: { toString(): string };
  email?: string;
}

interface WatchlistSymbolDoc {
  symbol: string;
}

export const getWatchlistSymbolsByEmail = async (email: string): Promise<string[]> => {
  try {
    if (!email) return [];

    const mongoose = await connectToDatabase();
    const db = mongoose.connection.db;
    if (!db) return [];

    const normalizedEmail = email.trim().toLowerCase();

    const user = (await db
      .collection<BetterAuthUserDoc>("user")
      .findOne({ email: normalizedEmail }, { projection: { id: 1, _id: 1, email: 1 } })) as BetterAuthUserDoc | null;

    if (!user) return [];

    const userId = user.id ?? user._id?.toString();
    if (!userId) return [];

    const items = await Watchlist.find({ userId })
      .select({ symbol: 1, _id: 0 })
      .lean<WatchlistSymbolDoc[]>();

    return (items || [])
      .map((i) => i.symbol)
      .filter((s): s is string => typeof s === "string" && s.length > 0);
  } catch (err) {
    console.error("getWatchlistSymbolsByEmail error:", err);
    return [];
  }
};

export type WatchlistItemDTO = {
  symbol: string;
  name: string;
  exchange: string;
  addedAt: number;
};

export const getMyWatchlist = async (): Promise<WatchlistItemDTO[]> => {
  try {
    const { userId } = await requireCurrentUser();
    await connectToDatabase();

    const items = await Watchlist.find({ userId })
      .select({ symbol: 1, company: 1, exchange: 1, addedAt: 1 })
      .sort({ addedAt: -1 })
      .lean<
        Array<{ symbol: string; company: string; exchange?: string; addedAt?: Date }>
      >();

    return (items || []).map((i) => ({
      symbol: String(i.symbol || "").toUpperCase(),
      name: String(i.company || i.symbol || "").trim() || String(i.symbol || "").toUpperCase(),
      exchange: String(i.exchange || "US").trim() || "US",
      addedAt: i.addedAt instanceof Date ? i.addedAt.getTime() : Date.now(),
    }));
  } catch (err) {
    console.error("getMyWatchlist error:", err);
    return [];
  }
};

export const addToMyWatchlist = async (item: {
  symbol: string;
  name: string;
  exchange: string;
}): Promise<{ success: boolean; error?: string }> => {
  try {
    const { userId } = await requireCurrentUser();
    await connectToDatabase();

    const symbol = String(item.symbol || "").toUpperCase().trim();
    const company = String(item.name || symbol).trim();
    const exchange = String(item.exchange || "US").trim() || "US";
    if (!symbol) return { success: false, error: "Symbol is required" };

    await Watchlist.updateOne(
      { userId, symbol },
      { $setOnInsert: { userId, symbol, company, exchange, addedAt: new Date() } },
      { upsert: true }
    );

    return { success: true };
  } catch (err) {
    console.error("addToMyWatchlist error:", err);
    return { success: false, error: err instanceof Error ? err.message : "Failed to add" };
  }
};

export const removeFromMyWatchlist = async (symbol: string): Promise<{ success: boolean; error?: string }> => {
  try {
    const { userId } = await requireCurrentUser();
    await connectToDatabase();

    const normalized = String(symbol || "").toUpperCase().trim();
    if (!normalized) return { success: false, error: "Symbol is required" };

    await Watchlist.deleteOne({ userId, symbol: normalized });
    return { success: true };
  } catch (err) {
    console.error("removeFromMyWatchlist error:", err);
    return { success: false, error: err instanceof Error ? err.message : "Failed to remove" };
  }
};

export const clearMyWatchlist = async (): Promise<{ success: boolean; error?: string }> => {
  try {
    const { userId } = await requireCurrentUser();
    await connectToDatabase();
    await Watchlist.deleteMany({ userId });
    return { success: true };
  } catch (err) {
    console.error("clearMyWatchlist error:", err);
    return { success: false, error: err instanceof Error ? err.message : "Failed to clear" };
  }
};
