import type { Metadata } from "next";
import MarketScopeClient from "./MarketScopeClient";

export const metadata: Metadata = {
  title: "Market Scope | Market Pulse",
  description: "Strong Money sector heatmap and top R-Factor leaders.",
};

export default function MarketScopePage() {
  return (
    <MarketScopeClient />
  );
}
