import { Spinner } from '@/components/spinner';
import { SubscriptionRequired } from '@/features/subscription/subscription-required';
import { useSubscription } from '@/features/subscription/use-subscription';

/**
 * Gates the analytics pages on an active subscription for the current league.
 *
 * Reads the current league's subscription state via {@link useSubscription},
 * which bypasses demo mode and the "no league connected" case (reporting active)
 * and treats a failed `getLeague` as active so the page still renders (the API
 * gate applies independently). While the status loads it shows a spinner;
 * otherwise it shows the inline paywall when the subscription is expired/absent.
 */
export function SubscriptionGuard({ children }: { children: React.ReactNode }) {
  const { loading, isActive } = useSubscription();

  if (loading)
    return (
      <div className="flex min-h-[70vh] items-center justify-center">
        <Spinner className="size-6 text-muted-foreground" />
      </div>
    );

  if (!isActive) return <SubscriptionRequired />;

  return <>{children}</>;
}
