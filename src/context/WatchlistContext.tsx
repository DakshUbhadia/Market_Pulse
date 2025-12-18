"use client"

import { createContext, useCallback, useContext, useMemo, useSyncExternalStore, type ReactNode } from "react"
import { getCuratedStockBySymbol } from "@/lib/constants"

export type WatchlistItem = {
  symbol: string
  name: string
  exchange: string
  addedAt: number
}

type WatchlistContextType = {
  watchlist: WatchlistItem[]
  isInWatchlist: (symbol: string) => boolean
  addToWatchlist: (item: Omit<WatchlistItem, "addedAt">) => void
  removeFromWatchlist: (symbol: string) => void
  toggleWatchlist: (item: Omit<WatchlistItem, "addedAt">) => boolean // returns new state
  clearWatchlist: () => void
}

const WatchlistContext = createContext<WatchlistContextType | null>(null)

const STORAGE_KEY = "market-pulse-watchlist"
const WATCHLIST_EVENT = "marketpulse:watchlist-changed"

function parseStoredWatchlist(raw: string | null): WatchlistItem[] {
  if (!raw) return []
  try {
    const parsed = JSON.parse(raw)
    if (Array.isArray(parsed)) return parsed
  } catch (error) {
    console.error("Failed to parse watchlist from localStorage:", error)
  }
  return []
}

function readStoredWatchlist(): WatchlistItem[] {
  if (typeof window === "undefined") return []
  return parseStoredWatchlist(localStorage.getItem(STORAGE_KEY))
}

function normalizeWatchlist(items: WatchlistItem[]): WatchlistItem[] {
  return items
    .filter((i) => i && typeof i === "object")
    .map((item) => {
      const symbol = String(item.symbol ?? "").toUpperCase().trim()
      const curated = getCuratedStockBySymbol(symbol)

      return {
        symbol,
        name: curated?.name ?? String(item.name ?? symbol),
        exchange: curated?.exchange ?? String(item.exchange ?? "US"),
        addedAt: typeof item.addedAt === "number" ? item.addedAt : Date.now(),
      }
    })
}

function writeStoredWatchlist(next: WatchlistItem[]) {
  if (typeof window === "undefined") return
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(next))
    // storage events don't fire in the same tab; use a custom event.
    window.dispatchEvent(new Event(WATCHLIST_EVENT))
  } catch (error) {
    console.error("Failed to save watchlist to localStorage:", error)
  }
}

function subscribe(callback: () => void) {
  if (typeof window === "undefined") return () => {}

  const onStorage = (e: StorageEvent) => {
    if (e.key === STORAGE_KEY) callback()
  }

  const onLocal = () => callback()

  window.addEventListener("storage", onStorage)
  window.addEventListener(WATCHLIST_EVENT, onLocal)
  return () => {
    window.removeEventListener("storage", onStorage)
    window.removeEventListener(WATCHLIST_EVENT, onLocal)
  }
}

let cachedRaw: string | null = null
let cachedSnapshot: WatchlistItem[] = []

function getSnapshot(): WatchlistItem[] {
  if (typeof window === "undefined") return []

  const raw = localStorage.getItem(STORAGE_KEY) ?? ""
  // React requires getSnapshot to be referentially stable when the underlying
  // store hasn't changed, otherwise it can trigger an infinite update loop.
  if (raw === cachedRaw) return cachedSnapshot

  cachedRaw = raw
  cachedSnapshot = normalizeWatchlist(parseStoredWatchlist(raw))
  return cachedSnapshot
}

function getServerSnapshot(): WatchlistItem[] {
  return []
}

export function WatchlistProvider({ children }: { children: ReactNode }) {
  // localStorage is the source of truth.
  // useSyncExternalStore also avoids SSR hydration mismatches.
  const watchlist = useSyncExternalStore(subscribe, getSnapshot, getServerSnapshot)

  const isInWatchlist = useCallback(
    (symbol: string) => {
      const normalized = symbol.toUpperCase()
      return watchlist.some((item) => item.symbol.toUpperCase() === normalized)
    },
    [watchlist]
  )

  const addToWatchlist = useCallback((item: Omit<WatchlistItem, "addedAt">) => {
    const prev = readStoredWatchlist()
    const normalized = item.symbol.toUpperCase()
    if (prev.some((i) => i.symbol.toUpperCase() === normalized)) return
    const next: WatchlistItem[] = [
      ...prev,
      {
        symbol: item.symbol.toUpperCase(),
        name: item.name,
        exchange: item.exchange,
        addedAt: Date.now(),
      },
    ]
    writeStoredWatchlist(next)
  }, [])

  const removeFromWatchlist = useCallback((symbol: string) => {
    const normalized = symbol.toUpperCase()
    const prev = readStoredWatchlist()
    const next = prev.filter((item) => item.symbol.toUpperCase() !== normalized)
    writeStoredWatchlist(next)
  }, [])

  const toggleWatchlist = useCallback(
    (item: Omit<WatchlistItem, "addedAt">) => {
      const normalized = item.symbol.toUpperCase()
      const exists = watchlist.some((i) => i.symbol.toUpperCase() === normalized)
      if (exists) {
        removeFromWatchlist(item.symbol)
        return false
      } else {
        addToWatchlist(item)
        return true
      }
    },
    [watchlist, addToWatchlist, removeFromWatchlist]
  )

  const clearWatchlist = useCallback(() => {
    writeStoredWatchlist([])
  }, [])

  const value = useMemo(
    () => ({
      watchlist,
      isInWatchlist,
      addToWatchlist,
      removeFromWatchlist,
      toggleWatchlist,
      clearWatchlist,
    }),
    [watchlist, isInWatchlist, addToWatchlist, removeFromWatchlist, toggleWatchlist, clearWatchlist]
  )

  return <WatchlistContext.Provider value={value}>{children}</WatchlistContext.Provider>
}

export function useWatchlist() {
  const context = useContext(WatchlistContext)
  if (!context) {
    throw new Error("useWatchlist must be used within a WatchlistProvider")
  }
  return context
}
