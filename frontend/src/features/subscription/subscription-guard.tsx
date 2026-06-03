import { Spinner } from '@/components/spinner';
import { SubscriptionRequired } from '@/features/subscription/subscription-required';
import { useSubscription } from '@/features/subscription/use-subscription';

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
  const { loading, isActive, activating } = useSubscription();

  if (loading || activating)
    return (
      <div className="flex min-h-[70vh] flex-col items-center justify-center gap-3">
        <Spinner className="size-6 text-muted-foreground" />
        {activating && (
          <p className="text-muted-foreground text-sm">
            Activating your subscription…
          </p>
        )}
      </div>
    );

  if (!isActive) return <SubscriptionRequired />;

  return <>{children}</>;
}
