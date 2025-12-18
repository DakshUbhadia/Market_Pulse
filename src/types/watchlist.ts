export type PriceHistory = {
  timestamp: number
  price: number
}

export type WatchlistStock = {
  id: string
  symbol: string
  name: string
  currentPrice: number
  openPrice: number
  highPrice: number
  lowPrice: number
  change?: number
  percentChange?: number
  peRatio: number
  logoUrl?: string
  exchange: "NASDAQ" | "BSE" | "NSE"
  currency?: "USD" | "INR"
  priceHistory?: PriceHistory[]
}

export type AlertCondition = "GREATER_THAN" | "LESS_THAN" | "CROSSES_ABOVE" | "CROSSES_BELOW"
export type AlertFrequency = "ONCE" | "HOURLY" | "DAILY" | "MINUTELY" | "CUSTOM"
export type AlertType = "PRICE" | "PERCENTAGE" | "PE_RATIO"

export type WatchlistAlert = {
  id: string
  name: string
  symbol: string
  stockName: string
  type: AlertType
  condition: AlertCondition
  threshold: number
  frequency: AlertFrequency
  isActive: boolean
  createdAt: Date
  lastTriggeredAt?: Date
}

export type SortConfig = {
  column: keyof WatchlistStock | "change" | "percentChange"
  direction: "asc" | "desc"
}
