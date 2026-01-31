import { Metadata } from 'next';
import { Suspense } from 'react';
import TradingTerminal from './TradingTerminal';
import TradingLoader from '@/components/ui/TradingLoader';

interface PageProps {
  readonly params: Promise<{ symbol: string }>;
}

export async function generateMetadata({ params }: PageProps): Promise<Metadata> {
  const { symbol } = await params;
  const decodedSymbol = decodeURIComponent(symbol);
  
  return {
    title: `Trade ${decodedSymbol} | Paper Trading Simulator | Market Pulse`,
    description: `Buy or sell ${decodedSymbol} with virtual money in the Paper Trading Simulator.`,
  };
}

export default async function TradingTerminalPage({ params }: PageProps) {
  const { symbol } = await params;
  const decodedSymbol = decodeURIComponent(symbol);
  
  return (
    <Suspense fallback={
      <div className="flex items-center justify-center min-h-[60vh]">
        <TradingLoader />
      </div>
    }>
      <TradingTerminal symbol={decodedSymbol} />
    </Suspense>
  );
}
