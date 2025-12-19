'use client'

import { useCallback, useEffect, useMemo, useRef, useState } from "react"
import { useRouter } from "next/navigation"
import { Loader2, Search, Star } from "lucide-react"
import { useWatchlist } from "@/context/WatchlistContext"
import { getCuratedStockBySymbol } from "@/lib/constants"

import {
  Command,
  CommandDialog,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from "@/components/ui/command"

import { searchStocks } from "@/lib/actions/finnhub.actions"

type StockResult = {
  symbol: string
  name: string
  exchange: string
  type: string
}

type SearchCommandProps = {
  open?: boolean
  onOpenChange?: (open: boolean) => void
  showTrigger?: boolean
}

const MOCK_STOCKS: StockResult[] = [
  { symbol: "AAPL", name: "Apple", exchange: "NASDAQ", type: "Stock" },
  { symbol: "RELIANCE", name: "Reliance Industries", exchange: "BSE", type: "Stock" },
  { symbol: "NVDA", name: "NVIDIA", exchange: "NASDAQ", type: "Stock" },
  { symbol: "TSLA", name: "Tesla", exchange: "NASDAQ", type: "Stock" },
  { symbol: "HDFCBANK", name: "HDFC Bank", exchange: "BSE", type: "Stock" },
  { symbol: "TATASTEEL", name: "Tata Steel", exchange: "BSE", type: "Stock" },
  { symbol: "GOOGL", name: "Alphabet (Google)", exchange: "NASDAQ", type: "Stock" },
  { symbol: "AMZN", name: "Amazon", exchange: "NASDAQ", type: "Stock" },
  { symbol: "META", name: "Meta", exchange: "NASDAQ", type: "Stock" },
];

const SearchCommand = ({
  open: controlledOpen,
  onOpenChange,
  showTrigger = true,
}: SearchCommandProps = {}) => {
  const router = useRouter()
  const { isInWatchlist, toggleWatchlist } = useWatchlist()
  const [openState, setOpenState] = useState(false)
  const [query, setQuery] = useState("")
  const [loading, setLoading] = useState(false)
  const [stocks, setStocks] = useState<StockResult[]>([])
  const lastRequestId = useRef(0)

  const isControlled = controlledOpen !== undefined
  const open = isControlled ? controlledOpen : openState

  const setOpen = useCallback(
    (value: boolean) => {
      if (!isControlled) {
        setOpenState(value)
      }

      onOpenChange?.(value)
    },
    [isControlled, onOpenChange]
  )

  useEffect(() => {
    const onKeyDown = (e: KeyboardEvent) => {
      const nav = navigator as Navigator & { userAgentData?: { platform?: string } }
      const platform = (nav.userAgentData?.platform ?? nav.platform ?? "").toString()
      const isMac = platform.toLowerCase().includes("mac")
      const isK = e.key.toLowerCase() === "k"
      const modifier = isMac ? e.metaKey : e.ctrlKey

      if (modifier && isK) {
        e.preventDefault()
        setOpen(true)
      }

      if (e.key === "Escape" && open) {
        e.preventDefault()
        setOpen(false)
      }
    }

    window.addEventListener("keydown", onKeyDown)
    return () => window.removeEventListener("keydown", onKeyDown)
  }, [open, setOpen])

  useEffect(() => {
    const onOpenSearch = () => setOpen(true)
    window.addEventListener("marketpulse:open-search", onOpenSearch)
    return () => window.removeEventListener("marketpulse:open-search", onOpenSearch)
  }, [setOpen])

  useEffect(() => {
    if (!open) return

    const requestId = ++lastRequestId.current
    const trimmed = query.trim()
    setLoading(true)

    const timer = window.setTimeout(async () => {
      try {
        const results = await searchStocks(trimmed || undefined)
        if (lastRequestId.current === requestId) {
          setStocks(results.map(r => ({
            symbol: r.symbol,
            name: r.name,
            exchange: r.exchange,
            type: r.type,
          })))
        }
      } catch (error) {
        console.error("Error in stock search:", error)
        if (lastRequestId.current === requestId) {
          setStocks([])
        }
      } finally {
        if (lastRequestId.current === requestId) {
          setLoading(false)
        }
      }
    }, 300)

    return () => window.clearTimeout(timer)
  }, [open, query])

  const handleQueryChange = (value: string) => {
    setQuery(value)
  };

  const handleSelectStock = (value: string) => {
    setOpen(false)
    router.push(`/stock/${encodeURIComponent(value.toUpperCase())}`)
  };

  const handleToggleWatchlist = (stock: StockResult, e: React.MouseEvent | React.KeyboardEvent) => {
    e.preventDefault()
    e.stopPropagation()
    const curated = getCuratedStockBySymbol(stock.symbol)
    toggleWatchlist({
      symbol: stock.symbol,
      name: curated?.name ?? stock.name,
      exchange: curated?.exchange ?? stock.exchange,
    })
  }

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase()

    const base: StockResult[] =
      stocks.length > 0
        ? stocks
        : MOCK_STOCKS

    if (!q) return base
    return base.filter(
      (s) => s.symbol.toLowerCase().includes(q) || s.name.toLowerCase().includes(q)
    )
  }, [query, stocks])

  return (
    <>
      {showTrigger ? (
        <Command className="w-full max-w-sm">
          <button
            type="button"
            onClick={() => setOpen(true)}
            className="flex w-full items-center gap-3 rounded-md border bg-background/40 px-3 py-2 text-left text-sm text-foreground shadow-sm ring-1 ring-yellow-500/10 transition-colors hover:bg-background/60"
          >
            <Search className="h-4 w-4 text-yellow-500/80" />
            <span className="flex-1 text-muted-foreground">Search stocks…</span>
            <span className="text-xs text-muted-foreground">Ctrl/Cmd K</span>
          </button>
        </Command>
      ) : null}

      <CommandDialog open={open} onOpenChange={setOpen}>
        <div className="flex items-center justify-between gap-3 border-b px-4 py-3">
          <div className="min-w-0">
            <div className="text-sm font-semibold text-foreground">Search</div>
            <div className="text-xs text-muted-foreground">
              Select a stock or star it for watchlist
            </div>
          </div>
          <div className="shrink-0 text-xs text-muted-foreground">Esc</div>
        </div>
        <CommandInput
          placeholder="Search stocks…"
          value={query}
          onValueChange={handleQueryChange}
          icon={<Search className="h-4 w-4 text-yellow-500/70" />}
          className="placeholder:text-muted-foreground"
        />

        <CommandList>
          {loading ? (
            <div className="flex items-center justify-center gap-2 p-8 text-sm text-muted-foreground">
              <Loader2 className="h-4 w-4 animate-spin text-yellow-500/80" />
              <span>Searching…</span>
            </div>
          ) : (
            <>
              {filtered.length === 0 ? (
                <CommandEmpty>No results found.</CommandEmpty>
              ) : null}
              <CommandGroup heading="Stocks">
                {filtered.map((stock) => {
                  const inWatchlist = isInWatchlist(stock.symbol)
                  return (
                    <CommandItem
                      key={stock.symbol}
                      value={stock.symbol}
                      onSelect={handleSelectStock}
                      className="group rounded-md px-3 py-2 hover:bg-yellow-500/10"
                    >
                      <span className="inline-flex h-7 w-12 items-center justify-center rounded-md border border-yellow-500/15 bg-yellow-500/10 text-xs font-semibold text-yellow-500">
                        {stock.symbol}
                      </span>
                      <span className="flex min-w-0 flex-1 flex-col text-left">
                        <span className="truncate text-sm text-foreground">{stock.name}</span>
                        <span className="truncate text-xs text-muted-foreground">
                          {stock.exchange || "US"}
                        </span>
                      </span>
                      <span
                        role="button"
                        tabIndex={0}
                        title={inWatchlist ? "Remove from watchlist" : "Add to watchlist"}
                        className={`ml-2 inline-flex h-9 w-9 items-center justify-center rounded-md border transition-colors ${
                          inWatchlist
                            ? "border-yellow-500/30 bg-yellow-500/20 text-yellow-500"
                            : "border-yellow-500/10 bg-background/20 text-muted-foreground hover:bg-yellow-500/10 hover:text-yellow-500"
                        }`}
                        onClick={(e) => handleToggleWatchlist(stock, e)}
                        onKeyDown={(e) => {
                          if (e.key === "Enter" || e.key === " ") {
                            handleToggleWatchlist(stock, e)
                          }
                        }}
                      >
                        <Star
                          className="h-4 w-4"
                          fill={inWatchlist ? "currentColor" : "none"}
                        />
                      </span>
                    </CommandItem>
                  )
                })}
              </CommandGroup>
            </>
          )}
        </CommandList>
      </CommandDialog>
    </>
  );
};

export default SearchCommand;
