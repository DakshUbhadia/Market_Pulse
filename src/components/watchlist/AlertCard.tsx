"use client"

import { motion } from "framer-motion"
import { Card } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Trash2, Edit2, Bell } from "lucide-react"
import type { WatchlistAlert } from "@/types/watchlist"
import { getCuratedStockBySymbol } from "@/lib/constants"

interface AlertCardProps {
  alert: WatchlistAlert
  onEdit: (alert: WatchlistAlert) => void
  onDelete: (alertId: string) => void
  onTest: (alert: WatchlistAlert) => void
}

export function AlertCard({ alert, onEdit, onDelete, onTest }: AlertCardProps) {
  const currencySymbol = (() => {
    const curated = getCuratedStockBySymbol(alert.symbol)
    return curated?.exchange === "BSE" || curated?.exchange === "NSE" ? "₹" : "$"
  })()
  const getConditionLabel = () => {
    const labels = {
      GREATER_THAN: "above",
      LESS_THAN: "below",
      CROSSES_ABOVE: "crosses above",
      CROSSES_BELOW: "crosses below",
    }
    return labels[alert.condition]
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
            Price <span className="text-gray-300 font-medium">{getConditionLabel()}</span>{" "}
            <span className="text-yellow-400 font-semibold">{currencySymbol}{alert.threshold.toFixed(2)}</span>
          </p>

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
              onClick={() => onTest(alert)}
              className="h-7 px-2 text-gray-400 hover:text-yellow-400 hover:bg-gray-700"
              title="Test alert"
            >
              <Bell className="h-3.5 w-3.5" />
            </Button>
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
