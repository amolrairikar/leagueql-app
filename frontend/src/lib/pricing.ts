import type { SubscriptionPlan } from '@/components/api/types';

/**
 * Canonical subscription prices, shared by the landing-page pricing table
 * (FE-001) and the in-app plan toggle (FE-022). This is the single source of
 * truth — update the amounts here only.
 */
export const SUBSCRIPTION_PRICES: Record<SubscriptionPlan, string> = {
  MONTHLY: '$1.99',
  YEARLY: '$8.99',
};
