import { useState } from 'react';

import { markCheckoutPending } from './use-subscription';

import {
  createBillingPortalSession,
  createCheckoutSession,
} from '@/components/api/billing';
import type { Platform } from '@/components/api/types';
import { ApiError, clearApiCache } from '@/lib/api-client';

/**
 * Drives the Stripe Checkout (FE-022) and Billing Portal (FE-023) redirects.
 *
 * Errors are surfaced by the global API error alert (mounted in `AppLayout`); this
 * hook only manages the per-action loading flags and the checkout-return marker.
 * On success the browser is redirected to Stripe, so the loading flag intentionally
 * stays set until navigation.
 */
export function useStripeBilling() {
  const [checkoutLoading, setCheckoutLoading] = useState(false);
  const [portalLoading, setPortalLoading] = useState(false);

  async function startCheckout(
    leagueId: string,
    platform: Platform,
  ): Promise<void> {
    if (checkoutLoading) return;
    setCheckoutLoading(true);
    try {
      const res = await createCheckoutSession(leagueId, platform);
      // Record the pending checkout so the return mount polls for activation.
      markCheckoutPending(leagueId);
      window.location.assign(res.data.url);
    } catch (err) {
      // A 409 means the league already has a subscription / in-flight checkout;
      // bust the cache so the next subscription read reflects reality. The error
      // (incl. the 409) is shown by the global ApiErrorAlert.
      if (err instanceof ApiError && err.status === 409) clearApiCache();
      setCheckoutLoading(false);
    }
  }

  /**
   * Opens the Stripe Billing Portal. Rethrows so the caller can fall back to
   * Checkout on a 404 (no Stripe customer yet — FE-023).
   */
  async function openBillingPortal(): Promise<void> {
    if (portalLoading) return;
    setPortalLoading(true);
    try {
      const res = await createBillingPortalSession();
      window.location.assign(res.data.url);
    } catch (err) {
      setPortalLoading(false);
      throw err;
    }
  }

  return { startCheckout, openBillingPortal, checkoutLoading, portalLoading };
}
