'use server';

import { headers } from "next/headers";
import { getAuth } from "@/lib/better-auth/auth";
import { connectToDatabase } from "@/database/mongoose";

interface BetterAuthUserDoc {
  id?: string;
  _id?: { toString(): string };
  email?: string;
}

export interface CurrentUserIdentity {
  userId: string;
  email: string;
}

export async function requireCurrentUser(): Promise<CurrentUserIdentity> {
  const auth = await getAuth();

  const isRecord = (v: unknown): v is Record<string, unknown> => typeof v === "object" && v !== null;

  // better-auth typings differ by version; treat session shape as unknown and narrow.
  const session: unknown = await auth.api.getSession({ headers: await headers() });

  const user = (() => {
    if (!isRecord(session)) return null;
    const directUser = session["user"];
    if (isRecord(directUser)) return directUser;
    const data = session["data"];
    if (!isRecord(data)) return null;
    const dataUser = data["user"];
    if (isRecord(dataUser)) return dataUser;
    return null;
  })();

  const rawEmail: unknown = user?.email;
  const email = typeof rawEmail === "string" ? rawEmail.trim().toLowerCase() : "";

  const rawUserId: unknown = user?.id ?? user?._id;
  const userIdFromSession = typeof rawUserId === "string" ? rawUserId : "";

  if (userIdFromSession && email) {
    return { userId: userIdFromSession, email };
  }

  if (!email) {
    throw new Error("Unauthorized");
  }

  // Fallback: resolve userId from the 'user' collection via email.
  const mongoose = await connectToDatabase();
  const db = mongoose.connection.db;
  if (!db) throw new Error("Database connection failed");

  const userDoc = (await db
    .collection<BetterAuthUserDoc>("user")
    .findOne({ email }, { projection: { id: 1, _id: 1, email: 1 } })) as BetterAuthUserDoc | null;

  const userId = userDoc?.id ?? userDoc?._id?.toString();
  if (!userId) throw new Error("Unauthorized");

  return { userId, email };
}
