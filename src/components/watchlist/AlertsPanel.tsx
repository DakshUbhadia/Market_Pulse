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
    <div className="flex h-full min-h-0 flex-col overflow-hidden rounded-xl border border-border bg-card">
      {/* Header */}
      <div className="border-b border-border p-5">
        <div className="mb-4 flex items-center gap-3">
          <div className="h-6 w-1.5 rounded-full bg-yellow-500" />
          <h2 className="text-xl font-semibold text-foreground">Alerts</h2>
        </div>
        <Button
          onClick={onCreateAlert}
          className="h-10 w-full gap-2 bg-yellow-600 font-semibold text-black hover:bg-yellow-700"
        >
          <Plus className="h-4 w-4" />
          Create Alert
        </Button>
      </div>

      {/* Alerts List (show ~3 cards, scroll for more) */}
      <ScrollArea className="h-[420px]">
        <div className="p-4 space-y-3">
          {alerts.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-8 text-center">
              <p className="text-sm text-muted-foreground">No alerts yet.</p>
              <p className="mt-1 text-xs text-muted-foreground/80">Create one to stay updated.</p>
            </div>
          ) : (
            <>
              {/* Active Alerts */}
              {activeAlerts.length > 0 && (
                <div>
                  <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
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
                <div className="mt-4 border-t border-border pt-4">
                  <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground/80">
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
        <div className="border-t border-border px-4 py-3 text-xs text-muted-foreground">
          <div className="flex justify-between">
            <span>{activeAlerts.length} active</span>
            <span>{pausedAlerts.length} paused</span>
          </div>
        </div>
      )}
    </div>
  )
}
