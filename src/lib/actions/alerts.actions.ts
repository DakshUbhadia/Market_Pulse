'use server';

import { sendAlertEmail, type AlertEmailData } from '@/lib/nodemailer';
import { getCuratedStockBySymbol } from '@/lib/constants';
import { connectToDatabase } from "@/database/mongoose";
import Alert from "@/database/models/alert.model";
import EmailPreferences from "@/database/models/email-preferences.model";
import { requireCurrentUser } from "@/lib/actions/session.actions";
import { Types } from "mongoose";

export type AlertType = 'PRICE' | 'PERCENTAGE' | 'PE_RATIO';
export type AlertCondition = 'GREATER_THAN' | 'LESS_THAN' | 'CROSSES_ABOVE' | 'CROSSES_BELOW';

export interface CheckAlertParams {
  alertId: string;
  alertName: string;
  symbol: string;
  stockName: string;
  exchange?: string;
  alertType: AlertType;
  condition: AlertCondition;
  threshold: number;
  prevValue?: number;
  currentPrice: number;
  percentChange?: number;
  peRatio?: number;
  userEmail?: string;
}

export interface CheckAlertResult {
  alertId: string;
  triggered: boolean;
  error?: string;
}

const formatCurrency = (value: number, symbol: string): string => {
  const curated = getCuratedStockBySymbol(symbol);
  const isIndian = curated?.exchange === 'BSE';
  const currencySymbol = isIndian ? '₹' : '$';
  return `${currencySymbol}${value.toFixed(2)}`;
};

const formatValue = (value: number, type: AlertType, symbol: string): string => {
  if (type === 'PERCENTAGE') {
    return `${value.toFixed(2)}%`;
  }
  if (type === 'PE_RATIO') {
    return value.toFixed(2);
  }
  return formatCurrency(value, symbol);
};

const checkCondition = (
  currentValue: number,
  threshold: number,
  condition: AlertCondition,
  prevValue?: number
): boolean => {
  if (!Number.isFinite(currentValue) || !Number.isFinite(threshold)) {
    return false;
  }

  // For true "cross" semantics we need a previous value snapshot.
  // If we don't have one yet, we treat it as not triggered and let the caller
  // store the current value for the next check.
  const hasPrev = typeof prevValue === 'number' && Number.isFinite(prevValue);

  switch (condition) {
    case 'GREATER_THAN':
      return currentValue > threshold;
    case 'LESS_THAN':
      return currentValue < threshold;
    case 'CROSSES_ABOVE':
      return hasPrev ? prevValue! <= threshold && currentValue > threshold : false;
    case 'CROSSES_BELOW':
      return hasPrev ? prevValue! >= threshold && currentValue < threshold : false;
    default:
      return false;
  }
};

const getCurrentValue = (params: CheckAlertParams): number | null => {
  switch (params.alertType) {
    case 'PRICE':
      return params.currentPrice;
    case 'PERCENTAGE':
      return params.percentChange ?? null;
    case 'PE_RATIO':
      return params.peRatio ?? null;
    default:
      return null;
  }
};

/**
 * Check if an alert condition is met and send email immediately if triggered.
 * This is a synchronous server action that sends the email right away.
 */
export async function checkAndTriggerAlert(
  params: CheckAlertParams
): Promise<CheckAlertResult> {
  try {
    const { userId, email } = await requireCurrentUser();
    await connectToDatabase();

    const prefs = await EmailPreferences.findOne({ userId })
      .select({ receiveAlerts: 1 })
      .lean<{ receiveAlerts?: boolean }>();

    if (prefs?.receiveAlerts === false) {
      return { alertId: params.alertId, triggered: false };
    }

    const currentValue = getCurrentValue(params);

    if (currentValue === null || !Number.isFinite(currentValue)) {
      return {
        alertId: params.alertId,
        triggered: false,
        error: `Unable to get current ${params.alertType} value for ${params.symbol}`,
      };
    }

    const isTriggered = checkCondition(currentValue, params.threshold, params.condition, params.prevValue);

    if (!isTriggered) {
      return {
        alertId: params.alertId,
        triggered: false,
      };
    }

    // Alert condition is met - send email immediately
    const timestamp = new Date().toLocaleString('en-US', {
      weekday: 'long',
      year: 'numeric',
      month: 'long',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      timeZoneName: 'short',
    });

    const resolvedEmail = email;

    const emailData: AlertEmailData = {
      email: resolvedEmail,
      alertName: params.alertName,
      symbol: params.symbol,
      company: params.stockName,
      currentPrice: formatValue(currentValue, params.alertType, params.symbol),
      targetPrice: formatValue(params.threshold, params.alertType, params.symbol),
      alertType: params.alertType,
      condition: params.condition,
      timestamp,
    };

    await sendAlertEmail(emailData);

    return {
      alertId: params.alertId,
      triggered: true,
    };
  } catch (error) {
    console.error('Error checking/triggering alert:', error);
    return {
      alertId: params.alertId,
      triggered: false,
      error: error instanceof Error ? error.message : 'Unknown error',
    };
  }
}

/**
 * Check multiple alerts and send emails for all triggered ones.
 * Returns which alerts were triggered.
 */
export async function checkAndTriggerMultipleAlerts(
  alertsToCheck: CheckAlertParams[]
): Promise<CheckAlertResult[]> {
  const results = await Promise.all(
    alertsToCheck.map((params) => checkAndTriggerAlert(params))
  );
  return results;
}

export type WatchlistAlertDTO = {
  id: string;
  name: string;
  symbol: string;
  stockName: string;
  exchange: string;
  type: AlertType;
  condition: AlertCondition;
  threshold: number;
  frequency: "ONCE" | "HOURLY" | "DAILY" | "MINUTELY" | "CUSTOM";
  isActive: boolean;
  createdAt: Date;
  lastTriggeredAt?: Date;
  deleteAt?: Date;
  lastObservedValue?: number;
  lastObservedAt?: Date;
};

export type CreateMyAlertInput = {
  name: string;
  symbol: string;
  stockName: string;
  exchange: string;
  type: AlertType;
  condition: AlertCondition;
  threshold: number;
  frequency: WatchlistAlertDTO["frequency"];
  isActive: boolean;
};

const toDTO = (doc: unknown): WatchlistAlertDTO => {
  const d = doc as Record<string, unknown>;
  return {
    id: String(d._id),
    name: String(d.name),
    symbol: String(d.symbol),
    stockName: String(d.stockName),
    exchange: String(d.exchange || "US"),
    type: d.type as AlertType,
    condition: d.condition as AlertCondition,
    threshold: Number(d.threshold),
    frequency: d.frequency as WatchlistAlertDTO["frequency"],
    isActive: Boolean(d.isActive),
    createdAt: d.createdAt instanceof Date ? d.createdAt : new Date(String(d.createdAt)),
    lastTriggeredAt: d.lastTriggeredAt instanceof Date ? d.lastTriggeredAt : (d.lastTriggeredAt ? new Date(String(d.lastTriggeredAt)) : undefined),
    deleteAt: d.deleteAt instanceof Date ? d.deleteAt : (d.deleteAt ? new Date(String(d.deleteAt)) : undefined),
    lastObservedValue: typeof d.lastObservedValue === "number" ? d.lastObservedValue : undefined,
    lastObservedAt: d.lastObservedAt instanceof Date ? d.lastObservedAt : (d.lastObservedAt ? new Date(String(d.lastObservedAt)) : undefined),
  };
};

export async function getMyAlerts(): Promise<WatchlistAlertDTO[]> {
  try {
    const { userId } = await requireCurrentUser();
    await connectToDatabase();

    const now = new Date();
    // Do not return already-expired alerts.
    const docs = await Alert.find({
      userId,
      $or: [{ deleteAt: { $exists: false } }, { deleteAt: { $gt: now } }],
    })
      .sort({ createdAt: -1 })
      .lean();

    return (docs || []).map(toDTO);
  } catch (err) {
    console.error("getMyAlerts error:", err);
    return [];
  }
}

export async function createMyAlert(input: CreateMyAlertInput): Promise<{ success: boolean; alert?: WatchlistAlertDTO; error?: string }> {
  try {
    const { userId } = await requireCurrentUser();
    await connectToDatabase();

    const doc = await Alert.create({
      userId,
      name: String(input.name).trim(),
      symbol: String(input.symbol).toUpperCase().trim(),
      stockName: String(input.stockName).trim(),
      exchange: String(input.exchange || "US").trim() || "US",
      type: input.type,
      condition: input.condition,
      threshold: input.threshold,
      frequency: input.frequency,
      isActive: input.isActive,
    });

    return { success: true, alert: toDTO(doc.toObject()) };
  } catch (err) {
    console.error("createMyAlert error:", err);
    return { success: false, error: err instanceof Error ? err.message : "Failed to create" };
  }
}

export async function updateMyAlert(alertId: string, input: Partial<Omit<WatchlistAlertDTO, "id" | "createdAt">>): Promise<{ success: boolean; alert?: WatchlistAlertDTO; error?: string }> {
  try {
    const { userId } = await requireCurrentUser();
    await connectToDatabase();

    const update: Record<string, unknown> = {};
    if (typeof input.name === "string") update.name = input.name.trim();
    if (typeof input.symbol === "string") update.symbol = input.symbol.toUpperCase().trim();
    if (typeof input.stockName === "string") update.stockName = input.stockName.trim();
    if (typeof input.exchange === "string") update.exchange = input.exchange.trim();
    if (typeof input.type === "string") update.type = input.type;
    if (typeof input.condition === "string") update.condition = input.condition;
    if (typeof input.threshold === "number") update.threshold = input.threshold;
    if (typeof input.frequency === "string") update.frequency = input.frequency;
    if (typeof input.isActive === "boolean") update.isActive = input.isActive;

    const doc = await Alert.findOneAndUpdate({ _id: alertId, userId }, { $set: update }, { new: true }).lean();
    if (!doc) return { success: false, error: "Alert not found" };
    return { success: true, alert: toDTO(doc) };
  } catch (err) {
    console.error("updateMyAlert error:", err);
    return { success: false, error: err instanceof Error ? err.message : "Failed to update" };
  }
}

export async function deleteMyAlert(alertId: string): Promise<{ success: boolean; error?: string }> {
  try {
    const { userId } = await requireCurrentUser();
    await connectToDatabase();
    await Alert.deleteOne({ _id: alertId, userId });
    return { success: true };
  } catch (err) {
    console.error("deleteMyAlert error:", err);
    return { success: false, error: err instanceof Error ? err.message : "Failed to delete" };
  }
}

export async function updateMyAlertObservations(updates: Array<{ alertId: string; lastObservedValue: number; lastObservedAt?: number }>): Promise<{ success: boolean; error?: string }> {
  try {
    const { userId } = await requireCurrentUser();
    await connectToDatabase();

    if (!Array.isArray(updates) || updates.length === 0) return { success: true };

    const bulk = Alert.collection.initializeUnorderedBulkOp();
    let count = 0;
    for (const u of updates) {
      if (!u || typeof u.alertId !== "string") continue;
      if (typeof u.lastObservedValue !== "number" || !Number.isFinite(u.lastObservedValue)) continue;

      const _id = new Types.ObjectId(u.alertId)
      bulk
        .find({ _id, userId })
        .updateOne({
          $set: {
            lastObservedValue: u.lastObservedValue,
            lastObservedAt: new Date(typeof u.lastObservedAt === "number" ? u.lastObservedAt : Date.now()),
          },
        });
      count++;
    }

    if (count === 0) return { success: true };
    await bulk.execute();
    return { success: true };
  } catch (err) {
    console.error("updateMyAlertObservations error:", err);
    return { success: false, error: err instanceof Error ? err.message : "Failed to update observations" };
  }
}

export async function markMyAlertsTriggered(triggered: Array<{ alertId: string; frequency: string }>): Promise<{ success: boolean; error?: string }> {
  try {
    const { userId } = await requireCurrentUser();
    await connectToDatabase();
    if (!Array.isArray(triggered) || triggered.length === 0) return { success: true };

    const now = Date.now();
    const bulk = Alert.collection.initializeUnorderedBulkOp();
    let count = 0;

    for (const t of triggered) {
      if (!t || typeof t.alertId !== "string") continue;
      const isOnce = String(t.frequency) === "ONCE";

      const _id = new Types.ObjectId(t.alertId)
      bulk
        .find({ _id, userId })
        .updateOne({
          $set: {
            lastTriggeredAt: new Date(now),
            ...(isOnce ? { deleteAt: new Date(now + 10 * 60_000) } : {}),
          },
        });
      count++;
    }

    if (count === 0) return { success: true };
    await bulk.execute();
    return { success: true };
  } catch (err) {
    console.error("markMyAlertsTriggered error:", err);
    return { success: false, error: err instanceof Error ? err.message : "Failed to mark triggered" };
  }
}
