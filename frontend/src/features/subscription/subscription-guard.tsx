import { Spinner } from '@/components/spinner';
import { SubscriptionRequired } from '@/features/subscription/subscription-required';
import { useSubscription } from '@/features/subscription/use-subscription';
import { isBillingEnabled } from '@/lib/feature-flags';

/**
 * Gates the analytics pages on an active subscription for the current league.
 *
 * Reads the current league's subscription state via {@link useSubscription},
 * which bypasses demo mode and the "no league connected" case (reporting active)
 * and treats a failed `getLeague` as active so the page still renders (the API
 * gate applies independently). While the status loads — or while a subscription
 * is activating after returning from Checkout (FE-022) — it shows a spinner;
 * otherwise it shows the inline paywall when the subscription is expired/absent.
 */
export function SubscriptionGuard({ children }: { children: React.ReactNode }) {
  // Billing is feature-flagged (FE-026). When off, the paywall and the
  // subscription polling in {@link useSubscription} are skipped entirely.
  if (!isBillingEnabled()) return <>{children}</>;
  return <SubscriptionGate>{children}</SubscriptionGate>;
}

function SubscriptionGate({ children }: { children: React.ReactNode }) {
  const { loading, isActive, activating, activationFailed } = useSubscription();

  if (loading || activating)
    return (
      <div className="flex flex-1 flex-col items-center justify-center gap-3">
        <Spinner className="size-6 text-muted-foreground" />
        {activating && (
          <p className="text-muted-foreground text-sm">
            Activating your subscription…
          </p>
        )}
      </div>
    );

  if (!isActive)
    return <SubscriptionRequired activationFailed={activationFailed} />;

  return <>{children}</>;
}
