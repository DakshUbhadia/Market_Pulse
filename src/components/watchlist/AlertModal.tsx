"use client"

import { useMemo, useState } from "react"
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import type { AlertType, AlertCondition, AlertFrequency, WatchlistAlert } from "@/types/watchlist"
import { getCuratedStockBySymbol } from "@/lib/constants"

interface AlertModalProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  onSave: (alert: Omit<WatchlistAlert, "id" | "createdAt">) => void
  prefilledSymbol?: string
  prefilledName?: string
  editingAlert?: WatchlistAlert | null
}

export function AlertModal({
  open,
  onOpenChange,
  onSave,
  prefilledSymbol,
  prefilledName,
  editingAlert,
}: AlertModalProps) {
  const [name, setName] = useState(editingAlert?.name || "")
  const [symbol, setSymbol] = useState(prefilledSymbol || editingAlert?.symbol || "")
  const [type, setType] = useState<AlertType>(editingAlert?.type || "PRICE")
  const [condition, setCondition] = useState<AlertCondition>(editingAlert?.condition || "GREATER_THAN")
  const [threshold, setThreshold] = useState(editingAlert?.threshold.toString() || "")
  const [frequency, setFrequency] = useState<AlertFrequency>(editingAlert?.frequency || "DAILY")
  const [isActive, setIsActive] = useState(editingAlert?.isActive !== false)

  const currencySymbol = useMemo(() => {
    if (!symbol) return "$"
    const curated = getCuratedStockBySymbol(symbol)
    return curated?.exchange === "BSE" || curated?.exchange === "NSE" ? "₹" : "$"
  }, [symbol])

  const isValid = name.trim() && symbol.trim() && threshold.trim() && !isNaN(parseFloat(threshold))

  const handleSave = () => {
    if (!isValid) return

    onSave({
      name: name.trim(),
      symbol: symbol.trim(),
      stockName: prefilledName || editingAlert?.stockName || symbol.trim(),
      type,
      condition,
      threshold: parseFloat(threshold),
      frequency,
      isActive,
      lastTriggeredAt: editingAlert?.lastTriggeredAt,
    })

    setName("")
    setSymbol("")
    setType("PRICE")
    setCondition("GREATER_THAN")
    setThreshold("")
    setFrequency("DAILY")
    setIsActive(true)
    onOpenChange(false)
  }

  const getSummary = () => {
    if (!symbol || !threshold) return "Alert not configured"
    const value = parseFloat(threshold)
    if (!Number.isFinite(value)) return "Alert not configured"

    if (type === "PERCENTAGE") {
      const conditionText = {
        GREATER_THAN: "% change above",
        LESS_THAN: "% change below",
        CROSSES_ABOVE: "% change crosses above",
        CROSSES_BELOW: "% change crosses below",
      }[condition]
      return `${conditionText} ${value.toFixed(2)}%`
    }

    if (type === "PE_RATIO") {
      const conditionText = {
        GREATER_THAN: "P/E above",
        LESS_THAN: "P/E below",
        CROSSES_ABOVE: "P/E crosses above",
        CROSSES_BELOW: "P/E crosses below",
      }[condition]
      return `${conditionText} ${value.toFixed(2)}`
    }

    const conditionText = {
      GREATER_THAN: "Price above",
      LESS_THAN: "Price below",
      CROSSES_ABOVE: "Price crosses above",
      CROSSES_BELOW: "Price crosses below",
    }[condition]
    return `${conditionText} ${currencySymbol}${value.toFixed(2)}`
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="bg-gray-900 border-gray-800 max-w-md">
        <DialogHeader>
          <DialogTitle className="text-gray-100">
            {editingAlert ? "Edit Alert" : "Create Alert"}
          </DialogTitle>
        </DialogHeader>

        <div className="space-y-4">
          {/* Alert Name */}
          <div className="space-y-2">
            <Label htmlFor="alert-name" className="text-gray-300">
              Alert Name
            </Label>
            <Input
              id="alert-name"
              placeholder="e.g., NVIDIA Recovery Alert"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="bg-gray-800 border-gray-700 text-gray-100 placeholder:text-gray-500"
            />
          </div>

          {/* Stock Symbol */}
          <div className="space-y-2">
            <Label htmlFor="alert-symbol" className="text-gray-300">
              Stock Symbol
            </Label>
            <Input
              id="alert-symbol"
              placeholder="AAPL, NVDA, etc."
              value={symbol}
              onChange={(e) => setSymbol(e.target.value.toUpperCase())}
              disabled={!!prefilledSymbol}
              className="bg-gray-800 border-gray-700 text-gray-100 placeholder:text-gray-500 disabled:opacity-50"
            />
          </div>

          {/* Alert Type */}
          <div className="space-y-2">
            <Label htmlFor="alert-type" className="text-gray-300">
              Alert Type
            </Label>
            <Select value={type} onValueChange={(v) => setType(v as AlertType)}>
              <SelectTrigger className="bg-gray-800 border-gray-700 text-gray-100">
                <SelectValue />
              </SelectTrigger>
              <SelectContent className="bg-gray-800 border-gray-700">
                <SelectItem value="PRICE" className="text-gray-100">
                  Price
                </SelectItem>
                <SelectItem value="PERCENTAGE" className="text-gray-100">
                  Percentage Change
                </SelectItem>
                <SelectItem value="PE_RATIO" className="text-gray-100">
                  P/E Ratio
                </SelectItem>
              </SelectContent>
            </Select>
          </div>

          {/* Condition */}
          <div className="space-y-2">
            <Label htmlFor="alert-condition" className="text-gray-300">
              Condition
            </Label>
            <Select value={condition} onValueChange={(v) => setCondition(v as AlertCondition)}>
              <SelectTrigger className="bg-gray-800 border-gray-700 text-gray-100">
                <SelectValue />
              </SelectTrigger>
              <SelectContent className="bg-gray-800 border-gray-700">
                <SelectItem value="GREATER_THAN" className="text-gray-100">
                  Greater than
                </SelectItem>
                <SelectItem value="LESS_THAN" className="text-gray-100">
                  Less than
                </SelectItem>
                <SelectItem value="CROSSES_ABOVE" className="text-gray-100">
                  Crosses above
                </SelectItem>
                <SelectItem value="CROSSES_BELOW" className="text-gray-100">
                  Crosses below
                </SelectItem>
              </SelectContent>
            </Select>
          </div>

          {/* Threshold Value */}
          <div className="space-y-2">
            <Label htmlFor="alert-threshold" className="text-gray-300">
              {type === "PERCENTAGE"
                ? "Percentage (%)"
                : type === "PE_RATIO"
                  ? "P/E Ratio"
                  : `Value (${currencySymbol})`}
            </Label>
            <Input
              id="alert-threshold"
              type="number"
              placeholder="Enter threshold"
              value={threshold}
              onChange={(e) => setThreshold(e.target.value)}
              step={type === "PERCENTAGE" ? "0.01" : "0.01"}
              className="bg-gray-800 border-gray-700 text-gray-100 placeholder:text-gray-500"
            />
          </div>

          {/* Frequency */}
          <div className="space-y-2">
            <Label htmlFor="alert-frequency" className="text-gray-300">
              Notification Frequency
            </Label>
            <Select value={frequency} onValueChange={(v) => setFrequency(v as AlertFrequency)}>
              <SelectTrigger className="bg-gray-800 border-gray-700 text-gray-100">
                <SelectValue />
              </SelectTrigger>
              <SelectContent className="bg-gray-800 border-gray-700">
                <SelectItem value="ONCE" className="text-gray-100">
                  Once
                </SelectItem>
                <SelectItem value="MINUTELY" className="text-gray-100">
                  Once per minute
                </SelectItem>
                <SelectItem value="HOURLY" className="text-gray-100">
                  Once per hour
                </SelectItem>
                <SelectItem value="DAILY" className="text-gray-100">
                  Once per day
                </SelectItem>
              </SelectContent>
            </Select>
          </div>

          {/* Summary Preview */}
          {name && (
            <div className="p-3 rounded-lg bg-gray-800/50 border border-gray-700">
              <p className="text-xs text-gray-400 mb-1">Alert Summary:</p>
              <p className="text-sm text-gray-200">
                {name} • <span className="text-yellow-400">{symbol}</span>
              </p>
              <p className="text-xs text-gray-400 mt-1">{getSummary()}</p>
            </div>
          )}
        </div>

        <DialogFooter className="gap-2">
          <Button
            variant="outline"
            onClick={() => onOpenChange(false)}
            className="border-gray-700 text-gray-300 hover:bg-gray-800"
          >
            Cancel
          </Button>
          <Button
            disabled={!isValid}
            onClick={handleSave}
            className="bg-yellow-600 hover:bg-yellow-700 text-black font-semibold"
          >
            {editingAlert ? "Save Changes" : "Create Alert"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
