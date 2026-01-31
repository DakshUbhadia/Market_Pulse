"use client"

import { createContext, useContext, useState, useCallback, useMemo, type ReactNode } from "react"

/**
 * Pages that require exclusive access to Yahoo Finance API to prevent
 * rate-limiting and ensure smooth real-time price updates.
 */
export type ExclusivePage = "simulator" | "market-scope" | "stock-detail" | null

type PageContextType = {
  /**
   * The currently active exclusive page. When set, background fetches
   * (like watchlist SSE) should be paused to avoid Yahoo Finance rate limits.
   */
  exclusivePage: ExclusivePage
  
  /**
   * Set when user navigates to a page that needs exclusive API access.
   * This will pause background watchlist fetches.
   */
  setExclusivePage: (page: ExclusivePage) => void
  
  /**
   * Clear the exclusive page (e.g., when leaving simulator/market-scope).
   */
  clearExclusivePage: () => void
  
  /**
   * Check if background fetches should be paused.
   */
  shouldPauseBackgroundFetches: boolean
}

const PageContext = createContext<PageContextType | null>(null)

interface PageProviderProps {
  readonly children: ReactNode
}

export function PageProvider({ children }: PageProviderProps) {
  const [exclusivePage, setExclusivePageInternal] = useState<ExclusivePage>(null)

  const setExclusivePage = useCallback((page: ExclusivePage) => {
    setExclusivePageInternal(page)
  }, [])

  const clearExclusivePage = useCallback(() => {
    setExclusivePageInternal(null)
  }, [])

  const shouldPauseBackgroundFetches = exclusivePage !== null

  const value = useMemo(
    () => ({
      exclusivePage,
      setExclusivePage,
      clearExclusivePage,
      shouldPauseBackgroundFetches,
    }),
    [exclusivePage, setExclusivePage, clearExclusivePage, shouldPauseBackgroundFetches]
  )

  return <PageContext.Provider value={value}>{children}</PageContext.Provider>
}

export function usePageContext() {
  const context = useContext(PageContext)
  if (!context) {
    throw new Error("usePageContext must be used within a PageProvider")
  }
  return context
}

/**
 * Hook to register a page as exclusive (pauses background fetches).
 * Call this at the top of simulator/market-scope pages.
 */
export function useExclusivePage(page: Exclude<ExclusivePage, null>) {
  const { setExclusivePage, clearExclusivePage } = usePageContext()
  
  // Using useEffect with stable deps
  const register = useCallback(() => {
    setExclusivePage(page)
    return () => {
      clearExclusivePage()
    }
  }, [page, setExclusivePage, clearExclusivePage])
  
  return register
}
