"use client"

import { motion } from "framer-motion"
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip"

interface DayRangeBarProps {
  low: number
  high: number
  current: number
  currencySymbol?: string
  onHover?: (shown: boolean) => void
}

export function DayRangeBar({ low, high, current, currencySymbol = "$", onHover }: DayRangeBarProps) {
  const hasNumbers = Number.isFinite(low) && Number.isFinite(high) && Number.isFinite(current)
  const range = hasNumbers ? high - low : 0
  const position = hasNumbers && range !== 0 ? ((current - low) / range) * 100 : 0

  const EMPTY_VALUE = "—"
  const fmt = (v: number) => (Number.isFinite(v) ? `${currencySymbol}${v.toFixed(2)}` : EMPTY_VALUE)

  return (
    <TooltipProvider>
      <Tooltip>
        <TooltipTrigger asChild>
          <div
            className="relative h-1.5 w-full cursor-pointer rounded-full bg-linear-to-r from-red-950 to-green-950"
            onMouseEnter={() => onHover?.(true)}
            onMouseLeave={() => onHover?.(false)}
          >
            {/* Animated dot */}
            <motion.div
              className="absolute top-1/2 -translate-y-1/2 -translate-x-1/2"
              style={{ left: `${position}%` }}
              initial={false}
              animate={{ left: `${position}%` }}
              transition={{ type: "spring", stiffness: 100, damping: 15 }}
            >
              <div className="relative">
                <div className="h-2 w-2 rounded-full border-2 border-yellow-400 bg-yellow-500/20 shadow-lg shadow-yellow-500/30" />
                <div className="absolute inset-0 h-2 w-2 rounded-full border-2 border-yellow-400 opacity-0 animate-pulse" />
              </div>
            </motion.div>
          </div>
        </TooltipTrigger>
        <TooltipContent className="bg-gray-900 border-gray-700 text-gray-100">
          <div className="flex items-center gap-2 text-sm">
            <span>{fmt(low)}</span>
            <span className="text-gray-500">•</span>
            <span className="font-semibold text-yellow-400">{fmt(current)}</span>
            <span className="text-gray-500">•</span>
            <span>{fmt(high)}</span>
          </div>
          <div className="text-xs text-gray-400 mt-1">
            {hasNumbers && range !== 0 ? `${((((current - low) / range) * 100) || 0).toFixed(0)}% of day range` : EMPTY_VALUE}
          </div>
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  )
}
