'use client';

import React from 'react';
import { createPortal } from 'react-dom';

import TradingLoader from '@/components/ui/TradingLoader';

export default function FullPageTradingLoader({
  show,
  label,
}: {
  show: boolean;
  label?: string;
}) {
  const [mounted, setMounted] = React.useState(false);

  React.useEffect(() => {
    setMounted(true);
  }, []);

  if (!show || !mounted) return null;

  return createPortal(
    <div
      className="fixed inset-0 flex items-center justify-center bg-black/70 backdrop-blur-md"
      style={{ zIndex: 2147483647 }}
      aria-live="polite"
      aria-busy="true"
    >
      <div className="flex w-60 max-w-[75vw] flex-col items-center gap-3">
        <TradingLoader />
        {label ? <p className="text-sm text-white/70">{label}</p> : null}
      </div>
    </div>,
    document.body,
  );
}
