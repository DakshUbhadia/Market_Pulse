"use client"

import * as React from "react"

import { cn } from "@/lib/utils"

type CommandDialogProps = {
  open: boolean
  onOpenChange: (open: boolean) => void
  children: React.ReactNode
}

function Command({ className, ...props }: React.ComponentProps<"div">) {
  return (
    <div
      data-slot="command"
      className={cn(
        "flex h-full w-full flex-col overflow-hidden rounded-md bg-popover text-popover-foreground",
        className
      )}
      {...props}
    />
  )
}

function CommandDialog({ open, onOpenChange, children }: CommandDialogProps) {
  if (!open) return null

  return (
    <div
      className="fixed inset-0 z-50"
      role="dialog"
      aria-modal="true"
      onMouseDown={() => onOpenChange(false)}
    >
      <div className="fixed inset-0 bg-black/70 backdrop-blur-md" />
      <div
        className="fixed left-1/2 top-[76px] z-50 w-[92vw] max-w-4xl -translate-x-1/2 overflow-hidden rounded-md border bg-popover text-popover-foreground shadow-md ring-1 ring-yellow-500/10 sm:w-[80vw] lg:w-[60vw]"
        onMouseDown={(e) => e.stopPropagation()}
      >
        {children}
      </div>
    </div>
  )
}

type CommandInputProps = Omit<React.ComponentProps<"input">, "onChange"> & {
  onValueChange?: (value: string) => void
  icon?: React.ReactNode
}

function CommandInput({ className, onValueChange, icon, ...props }: CommandInputProps) {
  return (
    <div
      className="flex items-center gap-2 border-b px-3"
      data-slot="command-input-wrapper"
    >
      {icon ? <div className="text-muted-foreground">{icon}</div> : null}
      <input
        data-slot="command-input"
        className={cn(
          "flex h-11 w-full rounded-md bg-transparent py-3 text-sm outline-hidden placeholder:text-muted-foreground disabled:cursor-not-allowed disabled:opacity-50",
          className
        )}
        onChange={(e) => onValueChange?.(e.target.value)}
        {...props}
      />
    </div>
  )
}

function CommandList({ className, ...props }: React.ComponentProps<"div">) {
  return (
    <div
      data-slot="command-list"
      className={cn("max-h-72 overflow-y-auto overflow-x-hidden", className)}
      {...props}
    />
  )
}

function CommandEmpty({ className, ...props }: React.ComponentProps<"div">) {
  return (
    <div
      data-slot="command-empty"
      className={cn("py-6 text-center text-sm text-muted-foreground", className)}
      {...props}
    />
  )
}

type CommandGroupProps = React.ComponentProps<"div"> & {
  heading?: string
}

function CommandGroup({ className, heading, children, ...props }: CommandGroupProps) {
  return (
    <div data-slot="command-group" className={cn("p-1", className)} {...props}>
      {heading ? (
        <div className="px-2 py-1.5 text-xs font-medium text-muted-foreground">{heading}</div>
      ) : null}
      <div className="flex flex-col">{children}</div>
    </div>
  )
}

type CommandItemProps = Omit<React.ComponentProps<"button">, "onSelect"> & {
  value: string
  onSelect?: (value: string) => void
}

function CommandItem({ className, value, onSelect, type, ...props }: CommandItemProps) {
  return (
    <button
      data-slot="command-item"
      type={type ?? "button"}
      className={cn(
        "relative flex w-full cursor-default items-center gap-2 rounded-sm px-2 py-1.5 text-sm outline-hidden select-none hover:bg-accent hover:text-accent-foreground",
        className
      )}
      onClick={() => onSelect?.(value)}
      {...props}
    />
  )
}

export {
  Command,
  CommandDialog,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
}
