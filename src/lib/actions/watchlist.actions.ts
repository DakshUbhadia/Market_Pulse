'use server';

import { connectToDatabase } from "@/database/mongoose";
import Watchlist from "@/database/models/watchlist.model";

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
