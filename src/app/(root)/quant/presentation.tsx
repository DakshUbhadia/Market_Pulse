import type { QuantStatus } from "@/lib/quant/status-contract";

export const panel = "rounded-xl border border-slate-700/70 bg-slate-950/50 p-5";
const title = "text-lg font-semibold text-slate-100";
const fmt = new Intl.NumberFormat("en-IN");
const ist = new Intl.DateTimeFormat("en-IN", {
  timeZone: "Asia/Kolkata", year: "numeric", month: "short", day: "numeric", hour: "numeric", minute: "2-digit",
});
type Details = Extract<QuantStatus, { schemaVersion: 2 }>["details"];
export type Snapshot = QuantStatus | undefined;

export function details(status: Snapshot) {
  return status?.schemaVersion === 2 ? status.details : undefined;
}

export function measured(status: Snapshot, key: keyof Details["metrics"]) {
  return details(status)?.metrics[key]?.value;
}

export function display(value: string | number | null | undefined): string {
  if (value == null) return "Not available";
  return typeof value === "number" ? fmt.format(value) : value;
}

export function dateLabel(value?: string | null): string {
  if (!value) return "Not available";
  return value.length === 10 ? value : ist.format(new Date(value)) + " IST";
}

export function state(value?: string) {
  return value?.replaceAll("_", " ").toLowerCase() ?? "Not available";
}

export function Fields({ items }: { items: [string, string | number | null | undefined][] }) {
  return <dl className="divide-y divide-slate-800">
    {items.map(([label, value]) => <div key={label} className="grid gap-1 py-2 sm:grid-cols-[minmax(9rem,1fr)_2fr] sm:gap-4">
      <dt className="text-slate-400">{label}</dt><dd className="break-all text-slate-100">{display(value)}</dd>
    </div>)}
  </dl>;
}

export function Card({ heading, children }: { heading: string; children: React.ReactNode }) {
  return <section className={panel}><h2 className={title}>{heading}</h2><div className="mt-3 space-y-3">{children}</div></section>;
}
