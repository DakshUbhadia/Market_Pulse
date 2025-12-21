"use client"

import { useState, useCallback, useEffect, useRef } from "react"
import { useRouter } from "next/navigation"
import { AlertModal } from "./AlertModal"
import { AlertsPanel } from "./AlertsPanel"
import { WatchlistTable } from "./WatchlistTable"
import { useToast } from "@/components/ui/use-toast"
import { useWatchlist } from "@/context/WatchlistContext"
import { getMultipleStockQuotes } from "@/lib/actions/finnhub.actions"
import {
  checkAndTriggerMultipleAlerts,
  createMyAlert,
  deleteMyAlert,
  getMyAlerts,
  markMyAlertsTriggered,
  updateMyAlert,
  updateMyAlertObservations,
  type CheckAlertParams,
} from "@/lib/actions/alerts.actions"
import { getCuratedStockBySymbol } from "@/lib/constants"
import { authClient } from "@/lib/auth-client"
import type { WatchlistStock, WatchlistAlert } from "@/types/watchlist"
import { Loader2, Plus, Star } from "lucide-react"
import { Button } from "@/components/ui/button"
const QUOTE_STREAM_INTERVAL_MS = 10_000

type StreamQuote = {
  symbol: string
  name?: string
  exchange?: string
  currency?: string
  currentPrice: number
  openPrice: number
  highPrice: number
  lowPrice: number
  change: number
  percentChange: number
  peRatio: number
  logoUrl?: string
}

const getCooldownMs = (frequency: WatchlistAlert["frequency"]) => {
  switch (frequency) {
    case "MINUTELY":
      return 60_000
    case "HOURLY":
      return 60 * 60_000
    case "DAILY":
      return 24 * 60 * 60_000
    case "ONCE":
      return Number.POSITIVE_INFINITY
    default:
      // CUSTOM isn't fully implemented in UI; default to minutely.
      return 60_000
  }
}

const getAlertCurrentValue = (alert: WatchlistAlert, stock?: WatchlistStock) => {
  if (!stock) return Number.NaN
  if (alert.type === "PRICE") return stock.currentPrice
  if (alert.type === "PERCENTAGE") return stock.percentChange ?? Number.NaN
  return stock.peRatio
}

const mapQuotesToWatchlistStocks = (args: {
  watchlist: Array<{ symbol: string; exchange?: string; name?: string }>
  quotes: StreamQuote[]
}): WatchlistStock[] => {
  const { watchlist, quotes } = args

  return watchlist.map((item) => {
    const curated = getCuratedStockBySymbol(item.symbol)
    const quote = quotes.find((q) => q.symbol.toUpperCase() === item.symbol.toUpperCase())

    if (quote) {
      const exchangeRaw = (curated?.exchange || item.exchange || quote.exchange || "US")
      const exchange = (exchangeRaw === "BSE" || exchangeRaw === "NSE" ? exchangeRaw : "NASDAQ") as "NASDAQ" | "BSE" | "NSE"
      const currency = exchange === "BSE" || exchange === "NSE" ? "INR" : ((quote.currency as "USD" | "INR" | undefined) ?? "USD")

      return {
        id: item.symbol,
        symbol: item.symbol,
        name: curated?.name || quote.name || item.name || item.symbol,
        exchange,
        currency,
        currentPrice: quote.currentPrice,
        openPrice: quote.openPrice,
        highPrice: quote.highPrice,
        lowPrice: quote.lowPrice,
        change: quote.change,
        percentChange: quote.percentChange,
        peRatio: quote.peRatio,
        logoUrl: quote.logoUrl,
      }
    }

    return {
      id: item.symbol,
      symbol: item.symbol,
      name: curated?.name || item.name || item.symbol,
      exchange: (curated?.exchange || item.exchange || "US") as "NASDAQ" | "BSE" | "NSE",
      currency: (curated?.exchange || item.exchange) === "BSE" || (curated?.exchange || item.exchange) === "NSE" ? "INR" : "USD",
      currentPrice: Number.NaN,
      openPrice: Number.NaN,
      highPrice: Number.NaN,
      lowPrice: Number.NaN,
      peRatio: Number.NaN,
    }
  })
}

const mergeStocksPreferValid = (prev: WatchlistStock[], next: WatchlistStock[]): WatchlistStock[] => {
  const prevBySymbol = new Map(prev.map((s) => [s.symbol.toUpperCase(), s] as const))

  return next.map((n) => {
    const p = prevBySymbol.get(n.symbol.toUpperCase())
    if (!p) return n

    const pickNumber = (value: number, fallback: number) => (Number.isFinite(value) ? value : fallback)
    const pickOptionalNumber = (value: number | undefined, fallback: number | undefined) =>
      typeof value === "number" && Number.isFinite(value) ? value : fallback

    const merged: WatchlistStock = {
      ...p,
      ...n,
      currentPrice: pickNumber(n.currentPrice, p.currentPrice),
      openPrice: pickNumber(n.openPrice, p.openPrice),
      highPrice: pickNumber(n.highPrice, p.highPrice),
      lowPrice: pickNumber(n.lowPrice, p.lowPrice),
      change: pickOptionalNumber(n.change, p.change),
      percentChange: pickOptionalNumber(n.percentChange, p.percentChange),
      peRatio: Number.isFinite(n.peRatio) && n.peRatio > 0 ? n.peRatio : p.peRatio,
    }

    return merged
  })
}

export function WatchlistPage() {
  const router = useRouter()
  const { toast } = useToast()
  const { watchlist, removeFromWatchlist } = useWatchlist()
  
  const [stocks, setStocks] = useState<WatchlistStock[]>([])
  const [loading, setLoading] = useState(true)
  const [alerts, setAlerts] = useState<WatchlistAlert[]>([])
  const [alertsHydrated, setAlertsHydrated] = useState(false)
  const [watchlistPanelHeight, setWatchlistPanelHeight] = useState<number | undefined>(undefined)
  const [modalOpen, setModalOpen] = useState(false)
  const [prefilledStock, setPrefilledStock] = useState<WatchlistStock | null>(null)
  const [editingAlert, setEditingAlert] = useState<WatchlistAlert | null>(null)

  const watchlistPanelRef = useRef<HTMLDivElement | null>(null)

  const lastTriggeredRef = useRef<Map<string, number>>(new Map())
  const warnedNoSessionRef = useRef(false)
  const alertsRef = useRef<WatchlistAlert[]>([])

  useEffect(() => {
    alertsRef.current = alerts
  }, [alerts])

  // Keep Alerts panel height aligned with the rendered Watchlist panel height.
  useEffect(() => {
    const el = watchlistPanelRef.current
    if (!el) return
    if (typeof ResizeObserver === "undefined") return

    const update = () => {
      const next = el.getBoundingClientRect().height
      if (Number.isFinite(next) && next > 0) {
        setWatchlistPanelHeight(next)
      }
    }

    update()
    const ro = new ResizeObserver(() => update())
    ro.observe(el)
    return () => ro.disconnect()
  }, [])

  // Load alerts from MongoDB once on mount.
  useEffect(() => {
    let cancelled = false

    const run = async () => {
      try {
        const session = await authClient.getSession()
        const userEmail = session?.data?.user?.email
        if (!userEmail) {
          if (!cancelled) {
            setAlerts([])
            setAlertsHydrated(true)
          }
          return
        }

        const dbAlerts = await getMyAlerts()
        if (!cancelled) {
          setAlerts(dbAlerts as unknown as WatchlistAlert[])
          setAlertsHydrated(true)
        }
      } catch (e) {
        console.error("Failed to load alerts:", e)
        if (!cancelled) {
          setAlerts([])
          setAlertsHydrated(true)
        }
      }
    }

    void run()
    return () => {
      cancelled = true
    }
  }, [])

  // Cleanup UI-only: remove alerts that reached deleteAt and delete them from DB.
  useEffect(() => {
    if (!alertsHydrated) return
    const now = Date.now()
    const expired = alerts.filter((a) => a.deleteAt instanceof Date && a.deleteAt.getTime() <= now)
    if (expired.length === 0) return

    setAlerts((prev) => prev.filter((a) => !(a.deleteAt instanceof Date && a.deleteAt.getTime() <= now)))
    for (const a of expired) {
      void deleteMyAlert(a.id)
    }
  }, [alerts, alertsHydrated])

  // Check alerts and send emails when stock data changes
  const checkAlertsAndSendEmails = useCallback(async (stockData: WatchlistStock[], currentAlerts: WatchlistAlert[]) => {
    const session = await authClient.getSession()
    const userEmail = session?.data?.user?.email
    
    if (!userEmail) {
      console.log("No user session, skipping alert email check")
      if (!warnedNoSessionRef.current) {
        warnedNoSessionRef.current = true
        toast({
          title: "Sign in required",
          description: "Sign in to receive email alerts.",
        })
      }
      return
    }

    // Filter active alerts based on their configured frequency + lastTriggeredAt.
    const now = Date.now()

    const activeAlerts = currentAlerts.filter((alert) => {
      if (!alert.isActive) return false
      if (alert.deleteAt instanceof Date && alert.deleteAt.getTime() <= now) return false

      // ONCE alerts should never trigger again once they fired.
      if (alert.frequency === "ONCE" && alert.lastTriggeredAt instanceof Date) return false

      const cooldownMs = getCooldownMs(alert.frequency)
      const lastTriggeredAtMs =
        alert.lastTriggeredAt instanceof Date ? alert.lastTriggeredAt.getTime() : 0

      // Extra in-memory protection (same tab) to prevent back-to-back sends.
      const lastTriggerRefMs = lastTriggeredRef.current.get(alert.id) ?? 0
      const effectiveLast = Math.max(lastTriggeredAtMs, lastTriggerRefMs)

      return now - effectiveLast >= cooldownMs
    })

    if (activeAlerts.length === 0) return

    const observationUpdates: Array<{ alertId: string; lastObservedValue: number; lastObservedAt?: number }> = []

    // Build params for each alert (include prevValue for real crossing detection)
    const alertParams: CheckAlertParams[] = activeAlerts.map((alert) => {
      const stock = stockData.find((s) => s.symbol.toUpperCase() === alert.symbol.toUpperCase())
      const currentValue = getAlertCurrentValue(alert, stock)
      if (Number.isFinite(currentValue)) {
        observationUpdates.push({ alertId: alert.id, lastObservedValue: currentValue, lastObservedAt: now })
      }

      return {
        alertId: alert.id,
        alertName: alert.name,
        symbol: alert.symbol,
        stockName: alert.stockName || stock?.name || alert.symbol,
        exchange: stock?.exchange,
        alertType: alert.type,
        condition: alert.condition,
        threshold: alert.threshold,
        prevValue: alert.lastObservedValue,
        currentPrice: stock?.currentPrice ?? Number.NaN,
        percentChange: stock?.percentChange,
        peRatio: stock?.peRatio,
        userEmail,
      }
    })

    try {
      if (observationUpdates.length > 0) {
        void updateMyAlertObservations(observationUpdates)
        setAlerts((prev) =>
          prev.map((a) => {
            const u = observationUpdates.find((x) => x.alertId === a.id)
            return u
              ? { ...a, lastObservedValue: u.lastObservedValue, lastObservedAt: new Date(u.lastObservedAt ?? now) }
              : a
          })
        )
      }

      const results = await checkAndTriggerMultipleAlerts(alertParams)

      const errors = results.filter((r) => r.error)
      if (errors.length > 0) {
        // Many "errors" are non-fatal (e.g., missing P/E for a symbol). Avoid spamming console/toasts.
        const first = errors[0]?.error || ""
        const isNonFatalValueMissing =
          typeof first === "string" &&
          (first.includes("Unable to get current") || first.includes("Missing user email") || first.includes("Unable to get current PE_RATIO"))

        if (isNonFatalValueMissing) {
          console.warn("Alert check skipped for some alerts:", errors)
        } else {
          console.error("Alert check returned errors:", errors)
          toast({
            title: "Alert email failed",
            description: first || "Unable to send one or more alert emails.",
          })
        }
      }

      // Update lastTriggered for any alerts that fired
      const triggeredIds = results.filter((r) => r.triggered).map((r) => r.alertId)
      
      if (triggeredIds.length > 0) {
        triggeredIds.forEach((id) => {
          lastTriggeredRef.current.set(id, now)
        })

        // Update alert lastTriggeredAt in state
        setAlerts((prev) => {
          const next = prev.map((a) => {
            if (!triggeredIds.includes(a.id)) return a

            const nextTriggeredAt = new Date(now)

            if (a.frequency === "ONCE") {
              // Delete ONCE alerts 10 minutes after they trigger.
              return { ...a, lastTriggeredAt: nextTriggeredAt, deleteAt: new Date(now + 10 * 60_000) }
            }

            return { ...a, lastTriggeredAt: nextTriggeredAt }
          })

          return next
        })

        void markMyAlertsTriggered(
          activeAlerts
            .filter((a) => triggeredIds.includes(a.id))
            .map((a) => ({ alertId: a.id, frequency: a.frequency }))
        )

        // Schedule deletion for ONCE alerts (best-effort; persisted deleteAt also handles refresh).
        const triggeredOnceAlerts = currentAlerts.filter(
          (a) => triggeredIds.includes(a.id) && a.frequency === "ONCE"
        )
        for (const a of triggeredOnceAlerts) {
          setTimeout(() => {
            setAlerts((prev) => prev.filter((x) => x.id !== a.id))
          }, 10 * 60_000)
        }

        // Show toast for triggered alerts
        toast({
          title: `${triggeredIds.length} Alert${triggeredIds.length > 1 ? "s" : ""} Triggered`,
          description: "Email notifications have been sent.",
        })
      }
    } catch (error) {
      console.error("Error checking alerts:", error)
      toast({
        title: "Alert email failed",
        description: error instanceof Error ? error.message : "Unknown error",
      })
    }
  }, [toast])

  // Fetch stock data when watchlist changes
  useEffect(() => {
    let cancelled = false
    let eventSource: EventSource | null = null

    const maybeCheckAlerts = (watchlistStocks: WatchlistStock[]) => {
      if (!alertsHydrated) return

      setTimeout(() => {
        if (cancelled) return
        checkAlertsAndSendEmails(watchlistStocks, alertsRef.current)
      }, 100)
    }

    async function fetchStockDataOnce() {
      if (watchlist.length === 0) {
        setStocks([])
        setLoading(false)
        return
      }

      setLoading(true)
      try {
        const quoteRequests = watchlist.map((item) => ({
          symbol: item.symbol,
          exchange: item.exchange,
        }))
        const quotes = await getMultipleStockQuotes(quoteRequests)

        const watchlistStocks = mapQuotesToWatchlistStocks({ watchlist, quotes })

        if (!cancelled) {
          setStocks(watchlistStocks)
          maybeCheckAlerts(watchlistStocks)
        }
      } catch (error) {
        console.error("Error fetching stock data:", error)
        toast({
          title: "Error",
          description: "Failed to fetch stock data. Please try again.",
        })
      } finally {
        setLoading(false)
      }
    }

    // Prefer SSE stream for real-time updates.
    const startStream = () => {
      if (typeof window === "undefined") return false
      if (typeof EventSource === "undefined") return false
      if (watchlist.length === 0) return false

      const items = watchlist.map((w) => ({ symbol: w.symbol, exchange: w.exchange }))
      const url = `/api/quotes/stream?items=${encodeURIComponent(JSON.stringify(items))}`
      const es = new EventSource(url)
      eventSource = es

      let receivedFirstPayload = false

      es.addEventListener("quotes", (evt) => {
        try {
          const payload = JSON.parse((evt as MessageEvent<string>).data) as { quotes?: unknown }
          const quotes = Array.isArray(payload?.quotes) ? (payload.quotes as StreamQuote[]) : []

          const watchlistStocks = mapQuotesToWatchlistStocks({ watchlist, quotes })
          setStocks((prev) => mergeStocksPreferValid(prev, watchlistStocks))
          maybeCheckAlerts(watchlistStocks)

          if (!receivedFirstPayload) {
            receivedFirstPayload = true
            setLoading(false)
          }
        } catch (e) {
          console.error("Failed to parse quote stream payload", e)
        }
      })

      es.addEventListener("error", (evt) => {
        try {
          const payload = JSON.parse((evt as MessageEvent<string>).data) as { message?: string }
          console.error("Quote stream error:", payload?.message)
        } catch {
          // ignore
        }
      })

      es.onerror = () => {
        es.close()
        if (!cancelled) {
          // Fall back to a one-shot fetch if the stream drops.
          void fetchStockDataOnce()
        }
      }

      // If we don't get any data quickly, fall back.
      setTimeout(() => {
        if (cancelled) return
        if (!receivedFirstPayload) {
          es.close()
          void fetchStockDataOnce()
        }
      }, Math.max(3_000, Math.floor(QUOTE_STREAM_INTERVAL_MS * 0.6)))

      return true
    }

    if (watchlist.length === 0) {
      setStocks([])
      setLoading(false)
    } else {
      setLoading(true)
      const started = startStream()
      if (!started) {
        void fetchStockDataOnce()
      }
    }

    return () => {
      cancelled = true
      eventSource?.close()
    }
  }, [watchlist, toast, checkAlertsAndSendEmails, alertsHydrated])

  const handleAddAlert = useCallback((stock: WatchlistStock) => {
    setPrefilledStock(stock)
    setEditingAlert(null)
    setModalOpen(true)
  }, [])

  const handleCreateAlertFromPanel = useCallback(() => {
    setPrefilledStock(null)
    setEditingAlert(null)
    setModalOpen(true)
  }, [])

  const handleEditAlert = useCallback((alert: WatchlistAlert) => {
    setEditingAlert(alert)
    setPrefilledStock(null)
    setModalOpen(true)
  }, [])

  const handleDeleteAlert = useCallback((alertId: string) => {
    setAlerts((prev) => prev.filter((a) => a.id !== alertId))
    void deleteMyAlert(alertId)
    toast({
      title: "Alert deleted",
      description: "The alert has been removed.",
    })
  }, [toast])


  const handleSaveAlert = useCallback(
    (alertData: Omit<WatchlistAlert, "id" | "createdAt">) => {
      const run = async () => {
        const exchange = getCuratedStockBySymbol(alertData.symbol)?.exchange || "US"

        if (editingAlert) {
          const res = await updateMyAlert(editingAlert.id, {
            name: alertData.name,
            symbol: alertData.symbol,
            stockName: alertData.stockName,
            exchange,
            type: alertData.type,
            condition: alertData.condition,
            threshold: alertData.threshold,
            frequency: alertData.frequency,
            isActive: alertData.isActive,
          })

          if (!res.success || !res.alert) {
            toast({ title: "Failed to update alert", description: res.error || "Unknown error" })
            return
          }

          setAlerts((prev) => prev.map((a) => (a.id === editingAlert.id ? (res.alert as unknown as WatchlistAlert) : a)))
          toast({ title: "Alert updated", description: `${alertData.name} has been updated.` })
          return
        }

        const res = await createMyAlert({
          name: alertData.name,
          symbol: alertData.symbol,
          stockName: alertData.stockName,
          exchange,
          type: alertData.type,
          condition: alertData.condition,
          threshold: alertData.threshold,
          frequency: alertData.frequency,
          isActive: alertData.isActive,
        })

        if (!res.success || !res.alert) {
          toast({ title: "Failed to create alert", description: res.error || "Unknown error" })
          return
        }

        setAlerts((prev) => [res.alert as unknown as WatchlistAlert, ...prev])
        toast({ title: "Alert created", description: "We'll notify you when conditions match." })
      }

      void run()
    },
    [editingAlert, toast]
  )

  const handleRemoveFromWatchlist = useCallback((symbol: string) => {
    removeFromWatchlist(symbol)
    toast({
      title: "Removed from watchlist",
      description: `${symbol} has been removed from your watchlist.`,
    })
  }, [removeFromWatchlist, toast])

  const handleViewStock = useCallback((symbol: string) => {
    router.push(`/stock/${encodeURIComponent(symbol)}`)
  }, [router])

  // Empty state
  if (!loading && watchlist.length === 0) {
    return (
      <div className="mx-auto w-full max-w-3xl py-10">
        <div className="rounded-xl border border-border bg-card p-8 text-center">
          <div className="mx-auto mb-5 flex h-20 w-20 items-center justify-center rounded-full bg-yellow-500/10">
            <Star className="h-10 w-10 text-yellow-500" />
          </div>
          <h2 className="mb-2 text-2xl font-semibold text-foreground">Your Watchlist is Empty</h2>
          <p className="mx-auto mb-6 max-w-md text-sm text-muted-foreground">
            Start tracking your favorite stocks by adding them to your watchlist.
            Search for stocks using the search bar or browse stock pages.
          </p>
          <Button
            onClick={() => {
              if (typeof window !== "undefined") {
                window.dispatchEvent(new Event("marketpulse:open-search"))
              }
            }}
            className="gap-2 bg-yellow-600 font-semibold text-black hover:bg-yellow-700"
          >
            <Plus className="h-4 w-4" />
            Browse Stocks
          </Button>
        </div>
      </div>
    )
  }

  return (
    <div className="grid h-full min-h-0 grid-cols-1 gap-8 lg:grid-cols-[1fr_320px]">
      {/* Watchlist Table */}
      <div className="flex min-h-0 flex-col">
        <div ref={watchlistPanelRef} className="rounded-xl border border-border bg-card p-5">
          <div className="mb-4 flex items-center gap-3">
            <div className="h-6 w-1.5 rounded-full bg-yellow-500" />
            <div>
              <h1 className="text-xl font-semibold text-foreground">Watchlist</h1>
              <p className="mt-1 text-sm text-muted-foreground">
                {watchlist.length} stock{watchlist.length !== 1 ? "s" : ""} in your watchlist
              </p>
            </div>
          </div>

          {loading ? (
            <div className="flex items-center justify-center py-20">
              <Loader2 className="h-8 w-8 animate-spin text-yellow-500" />
              <span className="ml-3 text-sm text-muted-foreground">Loading stock data...</span>
            </div>
          ) : (
            <div className="overflow-hidden rounded-lg border border-border/60 bg-background/40">
              <WatchlistTable
                stocks={stocks}
                onAddAlert={handleAddAlert}
                onRemoveStock={handleRemoveFromWatchlist}
                onViewStock={handleViewStock}
              />
            </div>
          )}
        </div>
      </div>

      {/* Alerts Panel */}
      <div className="flex min-h-0 flex-col">
        <AlertsPanel
          alerts={alerts}
          watchlistCount={watchlist.length}
          panelHeight={watchlistPanelHeight}
          onCreateAlert={handleCreateAlertFromPanel}
          onEditAlert={handleEditAlert}
          onDeleteAlert={handleDeleteAlert}
        />
      </div>

      {/* Alert Modal */}
      <AlertModal
        key={`${modalOpen ? "open" : "closed"}:${prefilledStock?.symbol ?? ""}:${editingAlert?.id ?? ""}`}
        open={modalOpen}
        onOpenChange={setModalOpen}
        onSave={handleSaveAlert}
        prefilledSymbol={prefilledStock?.symbol}
        prefilledName={prefilledStock?.name}
        editingAlert={editingAlert}
      />
    </div>
  )
}
