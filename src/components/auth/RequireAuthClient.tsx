'use client';

import React from 'react';
import { useRouter } from 'next/navigation';
import { authClient } from '@/lib/auth-client';

export default function RequireAuthClient({ children }: { children: React.ReactNode }) {
  const router = useRouter();

  React.useEffect(() => {
    let cancelled = false;

    const ensure = async () => {
      try {
        const session = await authClient.getSession();
        const hasUser = Boolean(session?.data?.user);
        if (!hasUser && !cancelled) {
          router.replace('/sign-in');
          return;
        }
      } catch {
        if (!cancelled) router.replace('/sign-in');
      }
    };

    // Initial check
    void ensure();

    // If the browser restores from BFCache (back/forward), force a reload
    // so middleware + session checks rerun and stale protected UI isn't shown.
    const onPageShow = (event: PageTransitionEvent) => {
      if (event.persisted) window.location.reload();
    };

    window.addEventListener('pageshow', onPageShow);

    return () => {
      cancelled = true;
      window.removeEventListener('pageshow', onPageShow);
    };
  }, [router]);

  return <>{children}</>;
}
