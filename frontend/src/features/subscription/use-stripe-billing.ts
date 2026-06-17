import { useState } from 'react';

import {
  createBillingPortalSession,
  createCheckoutSession,
} from '@/components/api/billing';
import type { Platform, SubscriptionPlan } from '@/components/api/types';
import { ApiError, clearApiCache } from '@/lib/api-client';

/**
 * Drives the Stripe Checkout (FE-022) and Billing Portal (FE-023) redirects.
 *
 * Owns the per-action loading flags and a shared `error` message that callers
 * render inline (e.g. via `ErrorAlert`) near the Subscribe / Manage billing
 * button. On success the browser is redirected to Stripe, so the loading flag
 * intentionally stays set until navigation.
 */
export function useStripeBilling() {
  const [checkoutLoading, setCheckoutLoading] = useState(false);
  const [portalLoading, setPortalLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function startCheckout(
    leagueId: string,
    platform: Platform,
    plan: SubscriptionPlan,
  ): Promise<void> {
    if (checkoutLoading) return;
    setError(null);
    setCheckoutLoading(true);
    try {
      // Send the current in-app path so both a successful checkout and a cancel
      // ("back") at Stripe return the user to the page they started checkout from
      // rather than /home (FE-022).
      const returnPath = window.location.pathname + window.location.search;
      const res = await createCheckoutSession(
        leagueId,
        platform,
        plan,
        returnPath,
      );
      // On a successful return, Stripe's success_url carries `?checkout=success`,
      // which drives the activation poll in useSubscription.
      window.location.assign(res.data.url);
    } catch (err) {
      // A 409 means the league already has a subscription / in-flight checkout;
      // bust the cache so the next subscription read reflects reality.
      if (err instanceof ApiError && err.status === 409) clearApiCache();
      setError(
        err instanceof ApiError ? err.message : 'Failed to start checkout.',
      );
      setCheckoutLoading(false);
    }
  }

  /**
   * Opens the Stripe Billing Portal. Rethrows so the caller can fall back to
   * Checkout on a 404 (no Stripe customer yet — FE-023); the 404 itself is not
   * recorded as an error since it triggers that fallback.
   */
  async function openBillingPortal(): Promise<void> {
    if (portalLoading) return;
    setError(null);
    setPortalLoading(true);
    try {
      const res = await createBillingPortalSession();
      window.location.assign(res.data.url);
    } catch (err) {
      setPortalLoading(false);
      if (!(err instanceof ApiError && err.status === 404)) {
        setError(
          err instanceof ApiError
            ? err.message
            : 'Failed to open billing portal.',
        );
      }
      throw err;
    }
  }

  return {
    startCheckout,
    openBillingPortal,
    checkoutLoading,
    portalLoading,
    error,
  };
}
