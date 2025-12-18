"use client"

import { motion } from "framer-motion"
import { Card } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Trash2, Edit2 } from "lucide-react"
import type { WatchlistAlert } from "@/types/watchlist"
import { getCuratedStockBySymbol } from "@/lib/constants"

interface AlertCardProps {
  alert: WatchlistAlert
  onEdit: (alert: WatchlistAlert) => void
  onDelete: (alertId: string) => void
}

export function AlertCard({ alert, onEdit, onDelete }: AlertCardProps) {
  const currencySymbol = (() => {
    const curated = getCuratedStockBySymbol(alert.symbol)
    return curated?.exchange === "BSE" || curated?.exchange === "NSE" ? "₹" : "$"
  })()

  const metricLabel = (() => {
    switch (alert.type) {
      case "PRICE":
        return "Price"
      case "PERCENTAGE":
        return "% Change"
      case "PE_RATIO":
        return "P/E Ratio"
      default:
        return "Value"
    }
  })()

  const formatThreshold = () => {
    if (!Number.isFinite(alert.threshold)) return "—"
    if (alert.type === "PRICE") return `${currencySymbol}${alert.threshold.toFixed(2)}`
    if (alert.type === "PERCENTAGE") return `${alert.threshold.toFixed(2)}%`
    return alert.threshold.toFixed(2)
  }

  const getConditionLabel = () => {
    const labels = {
      GREATER_THAN: "above",
      LESS_THAN: "below",
      CROSSES_ABOVE: "crosses above",
      CROSSES_BELOW: "crosses below",
    }
    return labels[alert.condition]
  }

  const getCrossoverMeaning = () => {
    if (alert.condition === "CROSSES_ABOVE") {
      return "Bullish crossover — often viewed as a buy signal."
    }
    if (alert.condition === "CROSSES_BELOW") {
      return "Bearish crossover — often viewed as a sell signal."
    }
    return null
  }

  const getFrequencyLabel = () => {
    const labels = {
      ONCE: "Once",
      MINUTELY: "Every min",
      HOURLY: "Every hour",
      DAILY: "Daily",
      CUSTOM: "Custom",
    }
    return labels[alert.frequency]
  }

  const formatDateUTC = (value: Date) => {
    try {
      return value.toISOString().slice(0, 10)
    } catch {
      return ""
    }
  }

  return (
    <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -10 }}>
      <Card className="bg-gray-800/50 border-gray-700 p-3 hover:bg-gray-800 transition-colors">
        <div className="space-y-2">
          {/* Header: Name and Status */}
          <div className="flex items-start justify-between gap-2">
            <div className="flex-1 min-w-0">
              <p className="text-sm font-semibold text-gray-100 truncate">{alert.name}</p>
              <div className="flex items-center gap-1.5 mt-0.5">
                <span className="text-xs font-mono text-yellow-400 bg-yellow-400/10 px-2 py-0.5 rounded">
                  {alert.symbol}
                </span>
                <Badge
                  variant={alert.isActive ? "default" : "secondary"}
                  className={`text-xs ${
                    alert.isActive
                      ? "bg-green-900/40 text-green-300 border-green-700"
                      : "bg-gray-700 text-gray-400"
                  }`}
                >
                  {alert.isActive ? "Active" : "Paused"}
                </Badge>
              </div>
            </div>
          </div>

          {/* Condition */}
          <p className="text-xs text-gray-400">
            {metricLabel} <span className="text-gray-300 font-medium">{getConditionLabel()}</span>{" "}
            <span className="text-yellow-400 font-semibold">{formatThreshold()}</span>
          </p>

          {getCrossoverMeaning() && (
            <p className="text-xs text-gray-500 leading-snug">
              {getCrossoverMeaning()}
            </p>
          )}

          {/* Frequency */}
          <div className="flex items-center justify-between">
            <span className="text-xs text-gray-500">{getFrequencyLabel()}</span>
            {alert.lastTriggeredAt && (
              <span className="text-xs text-gray-600">
                Last: {formatDateUTC(alert.lastTriggeredAt)}
              </span>
            )}
          </div>

          {/* Actions */}
          <div className="flex gap-1 pt-2 border-t border-gray-700">
            <Button
              size="sm"
              variant="ghost"
              onClick={() => onEdit(alert)}
              className="h-7 px-2 text-gray-400 hover:text-yellow-400 hover:bg-gray-700"
              title="Edit alert"
            >
              <Edit2 className="h-3.5 w-3.5" />
            </Button>
            <Button
              size="sm"
              variant="ghost"
              onClick={() => {
                if (confirm(`Delete alert "${alert.name}"?`)) {
                  onDelete(alert.id)
                }
              }}
              className="h-7 px-2 text-gray-400 hover:text-red-400 hover:bg-gray-700"
              title="Delete alert"
            >
              <Trash2 className="h-3.5 w-3.5" />
            </Button>
          </div>
        </div>
      </Card>
    </motion.div>
  )
}
