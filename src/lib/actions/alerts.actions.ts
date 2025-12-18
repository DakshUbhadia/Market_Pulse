'use server';

import { sendAlertEmail, type AlertEmailData } from '@/lib/nodemailer';
import { getCuratedStockBySymbol } from '@/lib/constants';

export type AlertType = 'PRICE' | 'PERCENTAGE' | 'PE_RATIO';
export type AlertCondition = 'GREATER_THAN' | 'LESS_THAN' | 'CROSSES_ABOVE' | 'CROSSES_BELOW';

export interface CheckAlertParams {
  alertId: string;
  alertName: string;
  symbol: string;
  stockName: string;
  alertType: AlertType;
  condition: AlertCondition;
  threshold: number;
  prevValue?: number;
  currentPrice: number;
  percentChange?: number;
  peRatio?: number;
  userEmail: string;
}

export interface CheckAlertResult {
  alertId: string;
  triggered: boolean;
  error?: string;
}

const formatCurrency = (value: number, symbol: string): string => {
  const curated = getCuratedStockBySymbol(symbol);
  const isIndian = curated?.exchange === 'BSE' || curated?.exchange === 'NSE';
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

    const emailData: AlertEmailData = {
      email: params.userEmail,
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
