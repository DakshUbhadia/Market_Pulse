import OptionsClient from './OptionsClient';

export const metadata = {
  title: 'Options Trading | Market Pulse',
  description: 'Advanced options analysis with real-time momentum radar, sector heatmaps, and F&O market scope for derivative traders',
};

/**
 * Options Trading Page (Server Component)
 *
 * Renders the F&O (Futures & Options) focused market analysis interface.
 * This page provides specialized tools for derivatives traders:
 * - Momentum radar for F&O eligible stocks
 * - Sector heatmaps and R-Factor analysis specific to the F&O basket
 * - Tom Hougaard strategy alerts
 *
 * The underlying data uses the F_O_stocks array from constants.ts,
 * bypassing the standard market toggle logic used in Market Scope.
 */
export default function OptionsPage() {
  return <OptionsClient />;
}