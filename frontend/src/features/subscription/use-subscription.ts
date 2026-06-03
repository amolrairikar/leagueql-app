import { useEffect, useState } from 'react';

import { getLeague } from '@/components/api/leagues';
import { getLeagueCookies, isDemoMode } from '@/lib/cookie-handler';

/** Days before `subscription_end_time` at which we flag the subscription as expiring soon. */
export const SUBSCRIPTION_EXPIRY_WARNING_DAYS = 14;

const DAY_MS = 24 * 60 * 60 * 1000;

export interface SubscriptionState {
  /** True while `getLeague` is in flight (never true for the bypass cases). */
  loading: boolean;
  /** `subscription_end_time` is present and in the future. */
  isActive: boolean;
  /** Active, but lapses within the warning window (14 days). */
  expiringSoon: boolean;
}

// Treated as active (page renders, no alert) so the API gate stays the single
// source of truth on a transient failure or in the bypass cases.
const ACTIVE: SubscriptionState = {
  loading: false,
  isActive: true,
  expiringSoon: false,
};

function deriveState(endTime?: string): SubscriptionState {
  const end = endTime ? new Date(endTime).getTime() : NaN;
  const now = Date.now();
  const isActive = !Number.isNaN(end) && end > now;
  const expiringSoon =
    isActive && end < now + SUBSCRIPTION_EXPIRY_WARNING_DAYS * DAY_MS;
  return { loading: false, isActive, expiringSoon };
}

/**
 * Reads the current league's `subscription_end_time` (per-league, via `getLeague`)
 * and derives its active / expiring-soon state. Shared by the analytics
 * `SubscriptionGuard` and the sidebar's "Manage Subscription" alert dot so both
 * read the same source through one fetch path.
 *
 * Demo mode and the "no league connected" case bypass the fetch and report an
 * active, non-expiring subscription (nothing to gate or warn about). A failed
 * request is treated as active as well, so the guard lets the page render and the
 * sidebar simply omits the dot.
 */
export function useSubscription(): SubscriptionState {
  const demoMode = isDemoMode();
  const { leagueId, platform } = getLeagueCookies();
  const bypass = demoMode || !leagueId;

  const [state, setState] = useState<SubscriptionState>(
    bypass ? ACTIVE : { loading: true, isActive: false, expiringSoon: false },
  );

  useEffect(() => {
    // `state` is already seeded to ACTIVE for the bypass case, and re-seeded by
    // the cleanup-guarded fetch below otherwise — avoid a synchronous setState
    // in the effect body (cascading renders).
    if (bypass) return;
    let cancelled = false;
    getLeague(leagueId, platform)
      .then((res) => {
        if (!cancelled) setState(deriveState(res.data.subscription_end_time));
      })
      .catch(() => {
        if (!cancelled) setState(ACTIVE);
      });
    return () => {
      cancelled = true;
    };
  }, [bypass, leagueId, platform]);

  return state;
}
