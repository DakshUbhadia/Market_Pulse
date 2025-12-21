"use client"

import { useState, useMemo } from "react"
import { motion, AnimatePresence } from "framer-motion"
import Image from "next/image"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { ArrowUpRight, ArrowDownRight, Plus, Trash2, ExternalLink } from "lucide-react"
import { DayRangeBar } from "./DayRangeBar"
import type { WatchlistStock, SortConfig } from "@/types/watchlist"

const EMPTY_VALUE = "—"

type SortColumn = SortConfig["column"]

function SortHeader({
  column,
  children,
  activeColumn,
  direction,
  onSort,
}: {
  column: SortColumn
  children: React.ReactNode
  activeColumn: SortColumn
  direction: SortConfig["direction"]
  onSort: (column: SortColumn) => void
}) {
  return (
    <TableHead
      onClick={() => onSort(column)}
      className="cursor-pointer select-none font-semibold text-muted-foreground hover:bg-muted/40"
    >
      <div className="flex items-center gap-1">
        {children}
        {activeColumn === column && (
          <span className="text-yellow-400">{direction === "asc" ? "↑" : "↓"}</span>
        )}
      </div>
    </TableHead>
  )
}

interface WatchlistTableProps {
  stocks: WatchlistStock[]
  onAddAlert: (stock: WatchlistStock) => void
  onRemoveStock?: (symbol: string) => void
  onViewStock?: (symbol: string) => void
  onSortChange?: (config: SortConfig) => void
  initialSort?: SortConfig
}

export function WatchlistTable({
  stocks,
  onAddAlert,
  onRemoveStock,
  onViewStock,
  onSortChange,
  initialSort = { column: "symbol", direction: "asc" },
}: WatchlistTableProps) {
  const [sortConfig, setSortConfig] = useState<SortConfig>(initialSort)

  const formatMoney = (currencySymbol: string, value: number) => {
    if (!Number.isFinite(value)) return EMPTY_VALUE
    return `${currencySymbol}${value.toFixed(2)}`
  }

  const handleSort = (column: SortColumn) => {
    const key = column as keyof WatchlistStock | "change" | "percentChange"
    const direction: "asc" | "desc" =
      sortConfig.column === key && sortConfig.direction === "asc" ? "desc" : "asc"
    const newConfig: SortConfig = { column: key, direction }
    setSortConfig(newConfig)
    onSortChange?.(newConfig)
  }

  const sortedStocks = useMemo(() => {
    const sorted = [...stocks].sort((a, b) => {
      let aVal: number | string
      let bVal: number | string

      if (sortConfig.column === "change") {
        const aChange =
          typeof a.change === "number" && Number.isFinite(a.change)
            ? a.change
            : (a.currentPrice - a.openPrice)
        const bChange =
          typeof b.change === "number" && Number.isFinite(b.change)
            ? b.change
            : (b.currentPrice - b.openPrice)
        aVal = Number.isFinite(aChange) ? aChange : 0
        bVal = Number.isFinite(bChange) ? bChange : 0
      } else if (sortConfig.column === "percentChange") {
        const aPct =
          typeof a.percentChange === "number" && Number.isFinite(a.percentChange)
          ? a.percentChange
          : (a.openPrice === 0 ? 0 : ((a.currentPrice - a.openPrice) / a.openPrice) * 100)
        const bPct =
          typeof b.percentChange === "number" && Number.isFinite(b.percentChange)
          ? b.percentChange
          : (b.openPrice === 0 ? 0 : ((b.currentPrice - b.openPrice) / b.openPrice) * 100)
        aVal = Number.isFinite(aPct) ? aPct : 0
        bVal = Number.isFinite(bPct) ? bPct : 0
      } else {
        const aValue = a[sortConfig.column as keyof WatchlistStock]
        const bValue = b[sortConfig.column as keyof WatchlistStock]
        if (typeof aValue === "string" && typeof bValue === "string") {
          aVal = aValue
          bVal = bValue
        } else if (typeof aValue === "number" && typeof bValue === "number") {
          aVal = aValue
          bVal = bValue
        } else {
          aVal = 0
          bVal = 0
        }
      }

      if (typeof aVal === "string") {
        return sortConfig.direction === "asc" ? aVal.localeCompare(bVal as string) : (bVal as string).localeCompare(aVal)
      }

      return sortConfig.direction === "asc"
        ? (aVal as number) - (bVal as number)
        : (bVal as number) - (aVal as number)
    })

    return sorted
  }, [stocks, sortConfig])

  return (
    <div className="overflow-hidden">
      {sortedStocks.length === 0 ? (
        <div className="py-8 text-center text-muted-foreground">
          <p>No stocks in watchlist. Add one to get started.</p>
        </div>
      ) : (
        <>
          {/* Desktop Table */}
          <div className="hidden sm:block overflow-x-auto">
            <Table>
              <TableHeader className="border-b border-border bg-muted/20">
                <TableRow className="hover:bg-transparent">
                  <SortHeader column="name" activeColumn={sortConfig.column} direction={sortConfig.direction} onSort={handleSort}>
                    Company
                  </SortHeader>
                  <SortHeader column="symbol" activeColumn={sortConfig.column} direction={sortConfig.direction} onSort={handleSort}>
                    Symbol
                  </SortHeader>
                  <SortHeader column="currentPrice" activeColumn={sortConfig.column} direction={sortConfig.direction} onSort={handleSort}>
                    Price
                  </SortHeader>
                  <SortHeader column="change" activeColumn={sortConfig.column} direction={sortConfig.direction} onSort={handleSort}>
                    Change
                  </SortHeader>
                  <SortHeader column="percentChange" activeColumn={sortConfig.column} direction={sortConfig.direction} onSort={handleSort}>
                    % Change
                  </SortHeader>
                  <TableHead className="font-semibold text-muted-foreground">Day&apos;s Range</TableHead>
                  <TableHead className="font-semibold text-muted-foreground">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                <AnimatePresence>
                  {sortedStocks.map((stock) => {
                    const hasPrices = Number.isFinite(stock.currentPrice) && Number.isFinite(stock.openPrice)
                    const computedChange = hasPrices ? stock.currentPrice - stock.openPrice : Number.NaN
                    const computedPercentChange =
                      hasPrices && stock.openPrice !== 0
                        ? (computedChange / stock.openPrice) * 100
                        : Number.NaN

                    // Prefer API values (Finnhub d/dp) when available.
                    const resolvedChange =
                      typeof stock.change === "number" && Number.isFinite(stock.change)
                        ? stock.change
                        : computedChange

                    const resolvedPercentChange =
                      typeof stock.percentChange === "number" && Number.isFinite(stock.percentChange)
                        ? stock.percentChange
                        : computedPercentChange
                    const isPositive = Number.isFinite(resolvedChange) ? resolvedChange >= 0 : true
                    const currencySymbol = stock.currency === "INR" || stock.exchange === "BSE" || stock.exchange === "NSE" ? "₹" : "$"

                    return (
                      <motion.tr
                        key={stock.id}
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        className="group border-b border-border/60 transition-colors hover:bg-muted/30"
                      >
                        {/* Company */}
                        <TableCell className="py-3 font-medium text-foreground">
                          <div 
                            className="flex cursor-pointer items-center gap-2 transition-colors hover:text-yellow-400"
                            onClick={() => onViewStock?.(stock.symbol)}
                          >
                            {stock.logoUrl ? (
                              <Image
                                src={stock.logoUrl}
                                alt={stock.name}
                                width={24}
                                height={24}
                                className="h-6 w-6 rounded-full"
                                unoptimized
                              />
                            ) : (
                              <div className="flex h-6 w-6 items-center justify-center rounded-full bg-muted text-xs font-bold text-muted-foreground">
                                {stock.symbol.charAt(0)}
                              </div>
                            )}
                            <span className="truncate">{stock.name}</span>
                          </div>
                        </TableCell>

                        {/* Symbol */}
                        <TableCell 
                          className="cursor-pointer py-3 font-mono text-sm text-yellow-300 transition-colors group-hover:text-yellow-400"
                          onClick={() => onViewStock?.(stock.symbol)}
                        >
                          {stock.symbol}
                        </TableCell>

                        {/* Price */}
                        <TableCell className="py-3 font-semibold text-foreground">
                          {formatMoney(currencySymbol, stock.currentPrice)}
                        </TableCell>

                        {/* Change */}
                        <TableCell className="py-3">
                          <div
                            className={`flex items-center gap-1 font-semibold ${
                              Number.isFinite(resolvedChange)
                                ? (isPositive ? "text-green-400" : "text-red-400")
                                : "text-muted-foreground"
                            }`}
                          >
                            {Number.isFinite(resolvedChange) ? (
                              isPositive ? <ArrowUpRight className="h-4 w-4" /> : <ArrowDownRight className="h-4 w-4" />
                            ) : null}
                            <span>
                              {Number.isFinite(resolvedChange)
                                ? formatMoney(currencySymbol, Math.abs(resolvedChange))
                                : EMPTY_VALUE}
                            </span>
                          </div>
                        </TableCell>

                        {/* % Change */}
                        <TableCell className="py-3">
                          <Badge
                            variant={Number.isFinite(resolvedPercentChange) && isPositive ? "default" : "secondary"}
                            className={`font-semibold ${
                              Number.isFinite(resolvedPercentChange)
                                ? (isPositive
                                    ? "bg-green-900/50 text-green-300 border-green-700"
                                    : "bg-red-900/50 text-red-300 border-red-700")
                                : "bg-gray-800 text-gray-400 border-gray-700"
                            }`}
                          >
                            {Number.isFinite(resolvedPercentChange)
                              ? `${isPositive ? "+" : ""}${resolvedPercentChange.toFixed(2)}%`
                              : EMPTY_VALUE}
                          </Badge>
                        </TableCell>

                        {/* Day's Range */}
                        <TableCell className="py-3 px-2">
                          <div className="w-32">
                            <DayRangeBar
                              low={stock.lowPrice}
                              high={stock.highPrice}
                              current={stock.currentPrice}
                              currencySymbol={currencySymbol}
                            />
                          </div>
                        </TableCell>

                        {/* Actions */}
                        <TableCell className="py-3">
                          <div className="flex items-center gap-1">
                            <Button
                              size="sm"
                              variant="ghost"
                              onClick={() => onViewStock?.(stock.symbol)}
                              className="h-8 w-8 p-0 text-gray-400 hover:text-yellow-400 hover:bg-yellow-500/10"
                              title="View stock details"
                            >
                              <ExternalLink className="h-3.5 w-3.5" />
                            </Button>
                            <Button
                              size="sm"
                              variant="outline"
                              onClick={() => onAddAlert(stock)}
                              className="border-yellow-600/30 text-yellow-400 hover:bg-yellow-600/10 gap-1 h-8 px-2"
                            >
                              <Plus className="h-3.5 w-3.5" />
                              <span className="text-xs hidden sm:inline">Alert</span>
                            </Button>
                            <Button
                              size="sm"
                              variant="ghost"
                              onClick={() => onRemoveStock?.(stock.symbol)}
                              className="h-8 w-8 p-0 text-gray-400 hover:text-red-400 hover:bg-red-500/10"
                              title="Remove from watchlist"
                            >
                              <Trash2 className="h-3.5 w-3.5" />
                            </Button>
                          </div>
                        </TableCell>
                      </motion.tr>
                    )
                  })}
                </AnimatePresence>
              </TableBody>
            </Table>
          </div>

          {/* Mobile Cards */}
          <div className="sm:hidden space-y-3 p-2">
            {sortedStocks.map((stock) => {
              const hasPrices = Number.isFinite(stock.currentPrice) && Number.isFinite(stock.openPrice)
              const computedChange = hasPrices ? stock.currentPrice - stock.openPrice : Number.NaN
              const computedPercentChange =
                hasPrices && stock.openPrice !== 0
                  ? (computedChange / stock.openPrice) * 100
                  : Number.NaN

              const resolvedChange =
                typeof stock.change === "number" && Number.isFinite(stock.change)
                  ? stock.change
                  : computedChange

              const resolvedPercentChange =
                typeof stock.percentChange === "number" && Number.isFinite(stock.percentChange)
                  ? stock.percentChange
                  : computedPercentChange
              const isPositive = Number.isFinite(resolvedChange) ? resolvedChange >= 0 : true
              const currencySymbol = stock.currency === "INR" || stock.exchange === "BSE" || stock.exchange === "NSE" ? "₹" : "$"

              return (
                <motion.div
                  key={`${stock.id}-mobile`}
                  initial={{ opacity: 0, y: 5 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -5 }}
                  className="rounded-xl border border-gray-800/80 bg-gray-900/70 p-4 shadow-lg shadow-black/40"
                >
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <p className="text-sm font-semibold text-gray-100 truncate">{stock.name}</p>
                      <p className="text-xs uppercase tracking-wide text-gray-500">{stock.symbol}</p>
                    </div>
                    <div className="text-right">
                      <p className="text-lg font-semibold text-gray-100">
                        {formatMoney(currencySymbol, stock.currentPrice)}
                      </p>
                      <Badge
                        variant={Number.isFinite(resolvedPercentChange) && isPositive ? "default" : "secondary"}
                        className={`text-xs font-semibold ${
                          Number.isFinite(resolvedPercentChange)
                            ? (isPositive
                                ? "bg-green-900/50 text-green-300 border-green-700"
                                : "bg-red-900/50 text-red-300 border-red-700")
                            : "bg-gray-800 text-gray-400 border-gray-700"
                        }`}
                      >
                        {Number.isFinite(resolvedPercentChange)
                          ? `${isPositive ? "+" : ""}${resolvedPercentChange.toFixed(2)}%`
                          : EMPTY_VALUE}
                      </Badge>
                    </div>
                  </div>

                  <div className="mt-3 grid grid-cols-2 gap-3 text-[11px] text-gray-400">
                    <div>
                      <p className="text-[10px] uppercase tracking-wide text-gray-500">Change</p>
                      <p className={`text-sm font-medium ${isPositive ? "text-green-300" : "text-red-300"}`}>
                        {Number.isFinite(resolvedChange)
                          ? `${isPositive ? "+" : ""}${formatMoney(currencySymbol, Math.abs(resolvedChange))}`
                          : EMPTY_VALUE}
                      </p>
                    </div>
                    <div>
                      <p className="text-[10px] uppercase tracking-wide text-gray-500">Open</p>
                      <p className="text-sm font-medium text-gray-100">
                        {formatMoney(currencySymbol, stock.openPrice)}
                      </p>
                    </div>
                  </div>

                  <div className="mt-4 flex items-center gap-2">
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => onViewStock?.(stock.symbol)}
                      className="h-8 w-8 p-0 text-gray-400 hover:text-yellow-400 hover:bg-yellow-500/10"
                      title="View stock details"
                    >
                      <ExternalLink className="h-3.5 w-3.5" />
                    </Button>
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => onAddAlert(stock)}
                      className="border-yellow-600/30 text-yellow-400 hover:bg-yellow-600/10 gap-1 h-8 px-2"
                    >
                      <Plus className="h-3.5 w-3.5" />
                      <span className="text-xs">Alert</span>
                    </Button>
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => onRemoveStock?.(stock.symbol)}
                      className="h-8 w-8 p-0 text-gray-400 hover:text-red-400 hover:bg-red-500/10"
                      title="Remove from watchlist"
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </Button>
                  </div>
                </motion.div>
              )
            })}
          </div>
        </>
      )}
    </div>
  )
}
