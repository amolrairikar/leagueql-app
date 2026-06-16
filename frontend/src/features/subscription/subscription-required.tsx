import { Lock } from 'lucide-react';
import { useState } from 'react';

import type { SubscriptionPlan } from '@/components/api/types';
import { Spinner } from '@/components/spinner';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { useIsOwner } from '@/features/ownership/use-is-owner';
import { PlanToggle } from '@/features/subscription/plan-toggle';
import { useStripeBilling } from '@/features/subscription/use-stripe-billing';
import { getLeagueCookies } from '@/lib/cookie-handler';
import { ErrorAlert } from '@/lib/error-alert';

/**
 * Locked-feature overlay shown in place of a premium feature when the current
 * league's subscription is expired or absent (freemium model, FE-021). It renders
 * a blurred, non-interactive skeleton of "a feature" behind a lock icon and the
 * Subscribe CTA, so the section reads as present-but-locked rather than missing.
 *
 * The gated component itself is **not** rendered (the guard swaps it for this), so
 * the premium feature's own data is never fetched while it is locked — only the
 * rest of the page keeps loading.
 *
 * `featureLabel` names the gated premium feature (e.g. "Schedule-swap simulator")
 * so the copy is feature-specific; when omitted the generic "Subscription
 * required" copy is shown.
 *
 * `activationFailed` is set when the user returned from Checkout but the
 * subscription never activated within the poll window (e.g. a webhook problem),
 * so they aren't left at a silent paywall after paying.
 */
export function SubscriptionRequired({
  activationFailed,
  featureLabel,
}: {
  activationFailed?: boolean;
  featureLabel?: string;
}) {
  const { startCheckout, checkoutLoading, error } = useStripeBilling();
  const { leagueId, platform } = getLeagueCookies();
  // Only the owner can subscribe (BE-016); non-owners are pointed at the owner
  // instead of a dead-end Subscribe button (FE-025).
  const { isOwner } = useIsOwner();
  const [plan, setPlan] = useState<SubscriptionPlan>('MONTHLY');

  return (
    <div className="relative overflow-hidden rounded-lg border border-border/50">
      {/* Decorative, non-interactive preview of the locked feature: a blurred
          skeleton so the section reads as content sitting behind the lock. */}
      <div
        aria-hidden
        className="pointer-events-none select-none space-y-3 p-4 opacity-60 blur-sm"
      >
        <Skeleton className="h-7 w-1/3" />
        <Skeleton className="h-40 w-full" />
        <div className="grid grid-cols-4 gap-2">
          <Skeleton className="h-6" />
          <Skeleton className="h-6" />
          <Skeleton className="h-6" />
          <Skeleton className="h-6" />
        </div>
      </div>

      {/* Lock + Subscribe overlay, centered over the blurred preview. */}
      <div className="bg-background/40 absolute inset-0 flex flex-col items-center justify-center gap-4 p-8 text-center backdrop-blur-[2px]">
        {activationFailed && (
          <Alert variant="destructive" className="max-w-md text-left">
            <AlertTitle>We couldn&apos;t confirm your subscription</AlertTitle>
            <AlertDescription>
              If you just completed payment, it can take a moment — refresh the
              page in a bit. If this keeps happening, contact support.
            </AlertDescription>
          </Alert>
        )}
        <div className="bg-muted flex size-12 items-center justify-center rounded-full">
          <Lock className="size-6 text-muted-foreground" />
        </div>
        <h2 className="text-xl font-bold">
          {featureLabel
            ? `${featureLabel} is a premium feature`
            : 'Subscription required'}
        </h2>
        {isOwner ? (
          <>
            <p className="text-muted-foreground max-w-md">
              {featureLabel
                ? `Subscribe to unlock ${featureLabel.toLowerCase()} and all other premium features for your league.`
                : "Subscribe to gain access to your league's analytics."}
            </p>
            <PlanToggle
              value={plan}
              onChange={setPlan}
              disabled={checkoutLoading}
            />
            <Button
              className="cursor-pointer"
              disabled={checkoutLoading || !leagueId}
              onClick={() => void startCheckout(leagueId, platform, plan)}
            >
              {checkoutLoading && <Spinner className="size-4" />}
              Subscribe
            </Button>
            {error && (
              <ErrorAlert message={error} className="max-w-md text-left" />
            )}
          </>
        ) : (
          <p className="text-muted-foreground max-w-md">
            {featureLabel
              ? `Ask the league owner to subscribe to unlock ${featureLabel.toLowerCase()}.`
              : "This league's subscription has lapsed. Ask the league owner to subscribe to restore access to its analytics."}
          </p>
        )}
      </div>
    </div>
  );
}
