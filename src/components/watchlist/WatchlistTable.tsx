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
      className="cursor-pointer select-none hover:bg-gray-800 text-gray-300 font-semibold"
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
    <div className="rounded-lg border border-gray-800 bg-gray-900/50 overflow-hidden">
      <div className="overflow-x-auto">
        <Table>
          <TableHeader className="bg-gray-800/30 border-b border-gray-800">
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
              <SortHeader column="peRatio" activeColumn={sortConfig.column} direction={sortConfig.direction} onSort={handleSort}>
                P/E
              </SortHeader>
              <TableHead className="text-gray-300 font-semibold">Day&apos;s Range</TableHead>
              <TableHead className="text-gray-300 font-semibold">Actions</TableHead>
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
                    className="border-b border-gray-800/50 hover:bg-gray-800/50 transition-colors group"
                  >
                    {/* Company */}
                    <TableCell className="py-3 text-gray-100 font-medium">
                      <div 
                        className="flex items-center gap-2 cursor-pointer hover:text-yellow-400 transition-colors"
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
                          <div className="h-6 w-6 rounded-full bg-gray-700 flex items-center justify-center text-xs font-bold text-gray-400">
                            {stock.symbol.charAt(0)}
                          </div>
                        )}
                        <span className="truncate">{stock.name}</span>
                      </div>
                    </TableCell>

                    {/* Symbol */}
                    <TableCell 
                      className="py-3 font-mono text-sm cursor-pointer group-hover:text-yellow-400 transition-colors text-yellow-300"
                      onClick={() => onViewStock?.(stock.symbol)}
                    >
                      {stock.symbol}
                    </TableCell>

                    {/* Price */}
                    <TableCell className="py-3 text-gray-100 font-semibold">
                      {formatMoney(currencySymbol, stock.currentPrice)}
                    </TableCell>

                    {/* Change */}
                    <TableCell className="py-3">
                      <div
                        className={`flex items-center gap-1 font-semibold ${
                          Number.isFinite(resolvedChange)
                            ? (isPositive ? "text-green-400" : "text-red-400")
                            : "text-gray-500"
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

                    {/* P/E Ratio */}
                    <TableCell className="py-3 text-gray-300 text-sm">
                      {Number.isFinite(stock.peRatio) && stock.peRatio > 0
                        ? stock.peRatio.toFixed(2)
                        : EMPTY_VALUE}
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

      {sortedStocks.length === 0 && (
        <div className="text-center py-8 text-gray-500">
          <p>No stocks in watchlist. Add one to get started.</p>
        </div>
      )}
    </div>
  )
}
