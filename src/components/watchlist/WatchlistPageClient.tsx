"use client"

import { useState, useCallback, useEffect, useRef } from "react"
import { useRouter } from "next/navigation"
import { AlertModal } from "./AlertModal"
import { AlertsPanel } from "./AlertsPanel"
import { WatchlistTable } from "./WatchlistTable"
import { useToast } from "@/components/ui/use-toast"
import { useWatchlist } from "@/context/WatchlistContext"
import { getMultipleStockQuotes } from "@/lib/actions/finnhub.actions"
import { getCuratedStockBySymbol } from "@/lib/constants"
import type { WatchlistStock, WatchlistAlert } from "@/types/watchlist"
import { Loader2, Plus, Star } from "lucide-react"
import { Button } from "@/components/ui/button"

const ALERTS_STORAGE_KEY = "marketpulse:watchlist-alerts:v1"

type StoredWatchlistAlert = Omit<WatchlistAlert, "createdAt" | "lastTriggeredAt"> & {
  createdAt: string
  lastTriggeredAt?: string
}

const parseStoredAlerts = (raw: string | null): WatchlistAlert[] => {
  if (!raw) return []
  try {
    const parsed = JSON.parse(raw) as unknown
    if (!Array.isArray(parsed)) return []

    const alerts: WatchlistAlert[] = []
    for (const item of parsed) {
      if (!item || typeof item !== "object") continue
      const a = item as Partial<StoredWatchlistAlert>

      if (typeof a.id !== "string" || !a.id) continue
      if (typeof a.name !== "string") continue
      if (typeof a.symbol !== "string") continue
      if (typeof a.stockName !== "string") continue
      if (typeof a.type !== "string") continue
      if (typeof a.condition !== "string") continue
      if (typeof a.threshold !== "number" || !Number.isFinite(a.threshold)) continue
      if (typeof a.frequency !== "string") continue
      if (typeof a.isActive !== "boolean") continue
      if (typeof a.createdAt !== "string" || !a.createdAt) continue

      const createdAt = new Date(a.createdAt)
      if (Number.isNaN(createdAt.getTime())) continue

      const lastTriggeredAt =
        typeof a.lastTriggeredAt === "string" && a.lastTriggeredAt
          ? new Date(a.lastTriggeredAt)
          : undefined

      alerts.push({
        id: a.id,
        name: a.name,
        symbol: a.symbol,
        stockName: a.stockName,
        type: a.type as WatchlistAlert["type"],
        condition: a.condition as WatchlistAlert["condition"],
        threshold: a.threshold,
        frequency: a.frequency as WatchlistAlert["frequency"],
        isActive: a.isActive,
        createdAt,
        lastTriggeredAt:
          lastTriggeredAt && !Number.isNaN(lastTriggeredAt.getTime()) ? lastTriggeredAt : undefined,
      })
    }

    return alerts
  } catch {
    return []
  }
}

const serializeAlerts = (alerts: WatchlistAlert[]): string => {
  const payload: StoredWatchlistAlert[] = alerts.map((a) => ({
    ...a,
    createdAt: a.createdAt instanceof Date ? a.createdAt.toISOString() : new Date(a.createdAt).toISOString(),
    lastTriggeredAt:
      a.lastTriggeredAt instanceof Date
        ? a.lastTriggeredAt.toISOString()
        : a.lastTriggeredAt
          ? new Date(a.lastTriggeredAt).toISOString()
          : undefined,
  }))
  return JSON.stringify(payload)
}

export function WatchlistPage() {
  const router = useRouter()
  const { toast } = useToast()
  const { watchlist, removeFromWatchlist } = useWatchlist()
  
  const [stocks, setStocks] = useState<WatchlistStock[]>([])
  const [loading, setLoading] = useState(true)
  const [alerts, setAlerts] = useState<WatchlistAlert[]>([])
  const [modalOpen, setModalOpen] = useState(false)
  const [prefilledStock, setPrefilledStock] = useState<WatchlistStock | null>(null)
  const [editingAlert, setEditingAlert] = useState<WatchlistAlert | null>(null)

  const didLoadAlertsRef = useRef(false)

  // Restore persisted alerts once on mount.
  useEffect(() => {
    if (typeof window === "undefined") return
    const restored = parseStoredAlerts(window.localStorage.getItem(ALERTS_STORAGE_KEY))
    setAlerts(restored)
    didLoadAlertsRef.current = true
  }, [])

  // Persist alerts whenever they change (after initial restore).
  useEffect(() => {
    if (typeof window === "undefined") return
    if (!didLoadAlertsRef.current) return
    window.localStorage.setItem(ALERTS_STORAGE_KEY, serializeAlerts(alerts))
  }, [alerts])

  // Fetch stock data when watchlist changes
  useEffect(() => {
    async function fetchStockData() {
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
        
        // Map quotes to WatchlistStock format, preserving watchlist metadata
        const watchlistStocks: WatchlistStock[] = watchlist.map((item) => {
          const curated = getCuratedStockBySymbol(item.symbol)
          const quote = quotes.find(
            (q) => q.symbol.toUpperCase() === item.symbol.toUpperCase()
          )
          
          if (quote) {
            const currency = (curated?.exchange || item.exchange || quote.exchange || "US") === "BSE" || (curated?.exchange || item.exchange || quote.exchange || "US") === "NSE"
              ? "INR"
              : ((quote.currency as "USD" | "INR" | undefined) ?? "USD")
            return {
              id: item.symbol,
              symbol: item.symbol,
              name: curated?.name || quote.name || item.name,
              exchange: (curated?.exchange || item.exchange || quote.exchange || "US") as "NASDAQ" | "BSE" | "NSE",
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
          
          // Fallback if quote not found
          return {
            id: item.symbol,
            symbol: item.symbol,
            name: curated?.name || item.name,
            exchange: (curated?.exchange || item.exchange || "US") as "NASDAQ" | "BSE" | "NSE",
            currency: (curated?.exchange || item.exchange) === "BSE" || (curated?.exchange || item.exchange) === "NSE" ? "INR" : "USD",
            currentPrice: Number.NaN,
            openPrice: Number.NaN,
            highPrice: Number.NaN,
            lowPrice: Number.NaN,
            peRatio: Number.NaN,
          }
        })
        
        setStocks(watchlistStocks)
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

    fetchStockData()
  }, [watchlist, toast])

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
    toast({
      title: "Alert deleted",
      description: "The alert has been removed.",
    })
  }, [toast])

  const handleTestAlert = useCallback((alert: WatchlistAlert) => {
    toast({
      title: "Test notification sent",
      description: `Testing alert: ${alert.name}`,
    })
  }, [toast])

  const handleSaveAlert = useCallback(
    (alertData: Omit<WatchlistAlert, "id" | "createdAt">) => {
      if (editingAlert) {
        setAlerts((prev) =>
          prev.map((a) =>
            a.id === editingAlert.id
              ? { ...a, ...alertData, id: a.id, createdAt: a.createdAt }
              : a
          )
        )
        toast({
          title: "Alert updated",
          description: `${alertData.name} has been updated.`,
        })
      } else {
        const newAlert: WatchlistAlert = {
          id: `alert-${Date.now()}`,
          ...alertData,
          createdAt: new Date(),
        }
        setAlerts((prev) => [newAlert, ...prev])
        toast({
          title: "Alert created",
          description: "We'll notify you when conditions match.",
        })
      }
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
      <div className="flex flex-col items-center justify-center py-20 text-center">
        <div className="mb-6 flex h-20 w-20 items-center justify-center rounded-full bg-yellow-500/10">
          <Star className="h-10 w-10 text-yellow-500" />
        </div>
        <h2 className="mb-2 text-2xl font-bold text-gray-100">Your Watchlist is Empty</h2>
        <p className="mb-6 max-w-md text-gray-500">
          Start tracking your favorite stocks by adding them to your watchlist.
          Search for stocks using the search bar or browse stock pages.
        </p>
        <Button
          onClick={() => {
            if (typeof window !== "undefined") {
              window.dispatchEvent(new Event("marketpulse:open-search"))
            }
          }}
          className="bg-yellow-600 hover:bg-yellow-700 text-black font-semibold gap-2"
        >
          <Plus className="h-4 w-4" />
          Browse Stocks
        </Button>
      </div>
    )
  }

  return (
    <div className="grid grid-cols-1 lg:grid-cols-[1fr_320px] gap-6 h-full">
      {/* Main Watchlist Table */}
      <div className="flex flex-col">
        <div className="mb-4">
          <h1 className="text-2xl font-bold text-gray-100">Watchlist</h1>
          <p className="text-sm text-gray-500 mt-1">
            {watchlist.length} stock{watchlist.length !== 1 ? "s" : ""} in your watchlist
          </p>
        </div>
        
        {loading ? (
          <div className="flex items-center justify-center py-20">
            <Loader2 className="h-8 w-8 animate-spin text-yellow-500" />
            <span className="ml-3 text-gray-400">Loading stock data...</span>
          </div>
        ) : (
          <WatchlistTable
            stocks={stocks}
            onAddAlert={handleAddAlert}
            onRemoveStock={handleRemoveFromWatchlist}
            onViewStock={handleViewStock}
          />
        )}
      </div>

      {/* Alerts Panel */}
      <div className="flex flex-col h-[600px] lg:h-full">
        <AlertsPanel
          alerts={alerts}
          onCreateAlert={handleCreateAlertFromPanel}
          onEditAlert={handleEditAlert}
          onDeleteAlert={handleDeleteAlert}
          onTestAlert={handleTestAlert}
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
