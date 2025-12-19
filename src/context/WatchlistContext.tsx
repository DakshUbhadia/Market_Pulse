"use client"

import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState, type ReactNode } from "react"
import { getCuratedStockBySymbol } from "@/lib/constants"
import { authClient } from "@/lib/auth-client"
import { addToMyWatchlist, clearMyWatchlist, getMyWatchlist, removeFromMyWatchlist } from "@/lib/actions/watchlist.actions"

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

const EMPTY_WATCHLIST: WatchlistItem[] = []

function normalizeSymbol(symbol: string): string {
  return String(symbol || "").toUpperCase().trim()
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

export function WatchlistProvider({ children }: { children: ReactNode }) {
  const [watchlist, setWatchlist] = useState<WatchlistItem[]>(EMPTY_WATCHLIST)
  const [sessionEmail, setSessionEmail] = useState<string | null>(null)
  const loadedRef = useRef(false)

  useEffect(() => {
    let cancelled = false

    const run = async () => {
      try {
        const session = await authClient.getSession()
        const email = session?.data?.user?.email

        if (!cancelled) setSessionEmail(typeof email === "string" ? email.trim().toLowerCase() : null)

        if (!email) {
          if (!cancelled) {
            loadedRef.current = true
            setWatchlist(EMPTY_WATCHLIST)
          }
          return
        }

        const items = await getMyWatchlist()
        if (cancelled) return
        loadedRef.current = true
        setWatchlist(normalizeWatchlist(items))
      } catch {
        if (!cancelled) {
          setSessionEmail(null)
          loadedRef.current = true
          setWatchlist(EMPTY_WATCHLIST)
        }
      }
    }

    void run()
    return () => {
      cancelled = true
    }
  }, [])

  const isInWatchlist = useCallback(
    (symbol: string) => {
      const normalized = normalizeSymbol(symbol)
      return watchlist.some((item) => item.symbol.toUpperCase() === normalized)
    },
    [watchlist]
  )

  const addToWatchlist = useCallback((item: Omit<WatchlistItem, "addedAt">) => {
    if (!sessionEmail) return
    const normalized = normalizeSymbol(item.symbol)
    if (!normalized) return

    setWatchlist((prev) => {
      if (prev.some((i) => i.symbol.toUpperCase() === normalized)) return prev
      return normalizeWatchlist([
        ...prev,
        { symbol: normalized, name: item.name, exchange: item.exchange, addedAt: Date.now() },
      ])
    })

    void addToMyWatchlist({ symbol: normalized, name: item.name, exchange: item.exchange })
  }, [sessionEmail])

  const removeFromWatchlist = useCallback((symbol: string) => {
    if (!sessionEmail) return
    const normalized = normalizeSymbol(symbol)
    if (!normalized) return
    setWatchlist((prev) => prev.filter((item) => item.symbol.toUpperCase() !== normalized))
    void removeFromMyWatchlist(normalized)
  }, [sessionEmail])

  const toggleWatchlist = useCallback(
    (item: Omit<WatchlistItem, "addedAt">) => {
      const normalized = normalizeSymbol(item.symbol)
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
    if (!sessionEmail) return
    setWatchlist(EMPTY_WATCHLIST)
    void clearMyWatchlist()
  }, [sessionEmail])

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
