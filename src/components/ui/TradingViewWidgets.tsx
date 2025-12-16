'use client';
import useTradingViewChart from '@/hooks/useTradingViewWidgets';
import { memo } from 'react';

interface TradingViewWidgetProps {
  title?: string;
  scriptURL: string;
  config: Record<string, unknown>;
  height: number;
  className?: string;
}

const TradingViewWidget = ({ scriptURL, config, height, className } : TradingViewWidgetProps) => {
  const containerRef = useTradingViewChart(scriptURL, config, height);
  return (
    <div 
      className={`tradingview-widget-container ${className || ''}`}
      ref={containerRef}
      style={{
        height: `${height}px`,
        width: '100%',
        boxSizing: 'border-box'
      }}
    />
  );
}

export default memo(TradingViewWidget);