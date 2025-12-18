"use client"

import { Button } from "@/components/ui/button"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Plus } from "lucide-react"
import { AlertCard } from "./AlertCard"
import type { WatchlistAlert } from "@/types/watchlist"
import { AnimatePresence } from "framer-motion"

interface AlertsPanelProps {
  alerts: WatchlistAlert[]
  onCreateAlert: () => void
  onEditAlert: (alert: WatchlistAlert) => void
  onDeleteAlert: (alertId: string) => void
}

export function AlertsPanel({
  alerts,
  onCreateAlert,
  onEditAlert,
  onDeleteAlert,
}: AlertsPanelProps) {
  const activeAlerts = alerts.filter((a) => a.isActive)
  const pausedAlerts = alerts.filter((a) => !a.isActive)

  return (
    <div className="flex flex-col h-full bg-linear-to-br from-gray-900 via-gray-900 to-gray-800/50 rounded-lg border border-gray-800 shadow-lg shadow-black/20 overflow-hidden">
      {/* Header */}
      <div className="p-4 border-b border-gray-800">
        <Button
          onClick={onCreateAlert}
          className="w-full bg-yellow-600 hover:bg-yellow-700 text-black font-semibold gap-2 h-10"
        >
          <Plus className="h-4 w-4" />
          Create Alert
        </Button>
      </div>

      {/* Alerts List (show ~3 cards, scroll for more) */}
      <ScrollArea className="h-[480px]">
        <div className="p-4 space-y-3">
          {alerts.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-8 text-center">
              <p className="text-gray-500 text-sm">No alerts yet.</p>
              <p className="text-gray-600 text-xs mt-1">Create one to stay updated.</p>
            </div>
          ) : (
            <>
              {/* Active Alerts */}
              {activeAlerts.length > 0 && (
                <div>
                  <p className="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-2">
                    Active ({activeAlerts.length})
                  </p>
                  <AnimatePresence>
                    {activeAlerts.map((alert) => (
                      <div key={alert.id} className="mb-2">
                        <AlertCard
                          alert={alert}
                          onEdit={onEditAlert}
                          onDelete={onDeleteAlert}
                        />
                      </div>
                    ))}
                  </AnimatePresence>
                </div>
              )}

              {/* Paused Alerts */}
              {pausedAlerts.length > 0 && (
                <div className="mt-4 pt-4 border-t border-gray-800">
                  <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">
                    Paused ({pausedAlerts.length})
                  </p>
                  <AnimatePresence>
                    {pausedAlerts.map((alert) => (
                      <div key={alert.id} className="mb-2">
                        <AlertCard
                          alert={alert}
                          onEdit={onEditAlert}
                          onDelete={onDeleteAlert}
                        />
                      </div>
                    ))}
                  </AnimatePresence>
                </div>
              )}
            </>
          )}
        </div>
      </ScrollArea>

      {/* Footer Stats */}
      {alerts.length > 0 && (
        <div className="px-4 py-3 border-t border-gray-800 bg-gray-800/20 text-xs text-gray-500">
          <div className="flex justify-between">
            <span>{activeAlerts.length} active</span>
            <span>{pausedAlerts.length} paused</span>
          </div>
        </div>
      )}
    </div>
  )
}
