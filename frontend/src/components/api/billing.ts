import type { BillingSessionResponse, Platform } from './types';

import { apiClient } from '@/lib/api-client';

/**
 * Stripe billing API accessors (BE-015). Both endpoints are POSTs (uncached) and
 * authenticate via the `__session` cookie that `apiClient` already attaches.
 */

/**
 * Create a Stripe Checkout Session to subscribe the given league and return the
 * Stripe-hosted URL to redirect to (FE-022).
 */
export function createCheckoutSession(
  leagueId: string,
  platform: Platform,
): Promise<BillingSessionResponse> {
  const params = new URLSearchParams({ platform });
  return apiClient.post<BillingSessionResponse>(
    `/leagues/${leagueId}/checkout-session?${params}`,
    {},
  );
}

/**
 * Create a Stripe Billing Portal Session for the current user and return the
 * Stripe-hosted URL to redirect to (FE-023).
 */
export function createBillingPortalSession(): Promise<BillingSessionResponse> {
  return apiClient.post<BillingSessionResponse>('/billing-portal-session', {});
}
