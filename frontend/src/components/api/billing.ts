import type {
  BillingSessionResponse,
  Platform,
  SubscriptionPlan,
} from './types';

import { apiClient } from '@/lib/api-client';

/**
 * Stripe billing API accessors (BE-015). Both endpoints are POSTs (uncached) and
 * authenticate via the Clerk session JWT that `apiClient` already attaches.
 */

/**
 * Create a Stripe Checkout Session to subscribe the given league on the chosen
 * plan (monthly or yearly) and return the Stripe-hosted URL to redirect to
 * (FE-022).
 *
 * `returnPath` is the in-app path the user started checkout from; the backend
 * uses it to build both the Checkout success and cancel ("back") URLs so that
 * completing or cancelling returns the user to that page rather than the
 * dashboard home.
 */
export function createCheckoutSession(
  leagueId: string,
  platform: Platform,
  plan: SubscriptionPlan,
  returnPath?: string,
): Promise<BillingSessionResponse> {
  const params = new URLSearchParams({ platform, plan });
  if (returnPath) params.set('returnPath', returnPath);
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
