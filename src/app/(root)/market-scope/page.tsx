import type { Metadata } from "next";
import MarketScopePanel from "@/components/analysis/MarketScopePanel";

export const metadata: Metadata = {
  title: "Market Scope | Market Pulse",
  description: "Strong Money sector heatmap and top R-Factor leaders.",
};

export default function MarketScopePage() {
  return (
    <div className="container mx-auto p-6 max-w-7xl">
      <MarketScopePanel />
    </div>
  );
}
