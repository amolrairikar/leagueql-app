import { useEffect, useState } from 'react';

import { getLeague } from '@/components/api/leagues';
import type { Platform } from '@/components/api/types';
import { clearApiCache } from '@/lib/api-client';
import { getLeagueCookies, isDemoMode } from '@/lib/cookie-handler';

/** Days before `subscription_end_time` at which we flag the subscription as expiring soon. */
export const SUBSCRIPTION_EXPIRY_WARNING_DAYS = 14;

const DAY_MS = 24 * 60 * 60 * 1000;

// Checkout return handling (FE-022): the backend records access asynchronously via
// the Stripe webhook, so after a *successful* Checkout (Stripe `success_url` carries
// `?checkout=success`) we poll (cache-busted) for a bounded window before falling
// back to the paywall. A cancel returns without the param, so it never polls.
const ACTIVATION_POLL_ATTEMPTS = 5;
const ACTIVATION_POLL_INTERVAL_MS = 2000;

export interface SubscriptionState {
  /** True while `getLeague` is in flight (never true for the bypass cases). */
  loading: boolean;
  /** `subscription_end_time` is present and in the future. */
  isActive: boolean;
  /** Active, but lapses within the warning window (14 days). */
  expiringSoon: boolean;
  /** Returning from Checkout and waiting for the webhook to record access. */
  activating: boolean;
  /** Returned from Checkout but the subscription never activated within the poll window. */
  activationFailed?: boolean;
  /** The raw `subscription_end_time`, when present (for status display). */
  endTime?: string;
}

// Treated as active (page renders, no alert) so the API gate stays the single
// source of truth on a transient failure or in the bypass cases.
const ACTIVE: SubscriptionState = {
  loading: false,
  isActive: true,
  expiringSoon: false,
  activating: false,
};

const LOADING: SubscriptionState = {
  loading: true,
  isActive: false,
  expiringSoon: false,
  activating: false,
};

const ACTIVATING: SubscriptionState = {
  loading: false,
  isActive: false,
  expiringSoon: false,
  activating: true,
};

/**
 * True when this mount is a return from a *successful* Checkout (the Stripe
 * `success_url` carries `?checkout=success`). Consumes the param via
 * `history.replaceState` so a refresh doesn't re-trigger the activation poll.
 */
function consumeCheckoutSuccess(): boolean {
  try {
    const params = new URLSearchParams(window.location.search);
    if (params.get('checkout') !== 'success') return false;
    params.delete('checkout');
    const query = params.toString();
    const url =
      window.location.pathname +
      (query ? `?${query}` : '') +
      window.location.hash;
    window.history.replaceState(null, '', url);
    return true;
  } catch {
    return false;
  }
}

export function deriveState(endTime?: string): SubscriptionState {
  const end = endTime ? new Date(endTime).getTime() : NaN;
  const now = Date.now();
  const isActive = !Number.isNaN(end) && end > now;
  const expiringSoon =
    isActive && end < now + SUBSCRIPTION_EXPIRY_WARNING_DAYS * DAY_MS;
  return { loading: false, isActive, expiringSoon, activating: false, endTime };
}

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

/**
 * Polls `fetchState` until it reports an active subscription or the attempts run
 * out, returning the final state. Extracted (with injectable `sleep`) so the
 * activation-polling logic is unit-testable without a React renderer.
 */
export async function pollUntilActive(
  fetchState: () => Promise<SubscriptionState>,
  opts: {
    attempts: number;
    intervalMs: number;
    sleep?: (ms: number) => Promise<void>;
  },
): Promise<SubscriptionState> {
  const wait = opts.sleep ?? sleep;
  let last = ACTIVATING;
  for (let attempt = 0; attempt < opts.attempts; attempt++) {
    last = await fetchState();
    if (last.isActive) return last;
    if (attempt < opts.attempts - 1) await wait(opts.intervalMs);
  }
  return last;
}

/**
 * Reads the current league's `subscription_end_time` (per-league, via `getLeague`)
 * and derives its active / expiring-soon state. Shared by the analytics
 * `SubscriptionGuard`, the sidebar's alert dot, and the Manage Subscription dialog
 * so they read the same source through one fetch path.
 *
 * Demo mode and the "no league connected" case bypass the fetch and report an
 * active, non-expiring subscription. A failed request is treated as active as
 * well, so the guard lets the page render and the sidebar omits the dot.
 *
 * On returning from Stripe Checkout (FE-022) it enters an `activating` state and
 * polls the cache-busted `getLeague` until the webhook-written subscription reads
 * active or the bounded attempts are exhausted.
 */
export function useSubscription(): SubscriptionState {
  const demoMode = isDemoMode();
  const { leagueId, platform } = getLeagueCookies();
  const bypass = demoMode || !leagueId;

  const [state, setState] = useState<SubscriptionState>(
    bypass ? ACTIVE : LOADING,
  );

  useEffect(() => {
    // Bypass (demo / no league) is already seeded to ACTIVE by the initial
    // useState; avoid a synchronous setState here (cascading renders).
    if (bypass) return;
    let cancelled = false;

    const fetchState = (): Promise<SubscriptionState> =>
      getLeague(leagueId, platform as Platform)
        .then((res) => deriveState(res.data.subscription_end_time))
        .catch(() => ACTIVE);

    const returning = consumeCheckoutSuccess();

    async function run() {
      if (returning) {
        setState(ACTIVATING);
        const result = await pollUntilActive(
          () => {
            clearApiCache();
            return fetchState();
          },
          {
            attempts: ACTIVATION_POLL_ATTEMPTS,
            intervalMs: ACTIVATION_POLL_INTERVAL_MS,
          },
        );
        // Returned from Checkout but never activated within the window — surface
        // it so the user isn't left at a silent paywall after paying.
        if (!cancelled)
          setState(
            result.isActive ? result : { ...result, activationFailed: true },
          );
      } else {
        const result = await fetchState();
        if (!cancelled) setState(result);
      }
    }

    void run();
    return () => {
      cancelled = true;
    };
  }, [bypass, leagueId, platform]);

  return state;
}
