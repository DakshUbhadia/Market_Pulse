import { Metadata } from 'next';
import SimulatorDashboard from './SimulatorDashboard';

export const metadata: Metadata = {
  title: 'Paper Trading Simulator | Market Pulse',
  description: 'Practice trading with ₹1,00,000 virtual money. No risk, real learning.',
};

export default function SimulatorPage() {
  return <SimulatorDashboard />;
}
