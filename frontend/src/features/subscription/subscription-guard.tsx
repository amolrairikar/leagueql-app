import { useEffect, useState } from 'react';

import { getLeague } from '@/components/api/leagues';
import { Spinner } from '@/components/spinner';
import { SubscriptionRequired } from '@/features/subscription/subscription-required';
import { getLeagueCookies, isDemoMode } from '@/lib/cookie-handler';

type GateState = 'loading' | 'allowed' | 'blocked';

function isActive(subscriptionEndTime?: string): boolean {
  if (!subscriptionEndTime) return false;
  const end = new Date(subscriptionEndTime).getTime();
  if (Number.isNaN(end)) return false;
  return end > Date.now();
}

/**
 * Gates the analytics pages on an active subscription for the current league.
 *
 * Demo mode bypasses the gate entirely, and so does the "no league connected"
 * case (there is nothing to gate) — both start in the `allowed` state. Otherwise
 * it reads `subscription_end_time` via `getLeague` and shows the inline paywall
 * when the subscription is expired or absent. While the status loads it shows a
 * spinner. If the request fails it falls through to the page (the API still
 * enforces the gate independently).
 */
export function SubscriptionGuard({ children }: { children: React.ReactNode }) {
  const demoMode = isDemoMode();
  const { leagueId, platform } = getLeagueCookies();
  const bypass = demoMode || !leagueId;
  const [state, setState] = useState<GateState>(bypass ? 'allowed' : 'loading');

  useEffect(() => {
    if (bypass) return;
    let cancelled = false;
    getLeague(leagueId, platform)
      .then((res) => {
        if (cancelled) return;
        setState(
          isActive(res.data.subscription_end_time) ? 'allowed' : 'blocked',
        );
      })
      .catch(() => {
        // Transient/load error — let the page render; the API gate still applies.
        if (!cancelled) setState('allowed');
      });
    return () => {
      cancelled = true;
    };
  }, [bypass, leagueId, platform]);

  if (state === 'loading')
    return (
      <div className="flex min-h-[70vh] items-center justify-center">
        <Spinner className="size-6 text-muted-foreground" />
      </div>
    );

  if (state === 'blocked') return <SubscriptionRequired />;

  return <>{children}</>;
}
