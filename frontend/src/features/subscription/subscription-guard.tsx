import { Spinner } from '@/components/spinner';
import { SubscriptionRequired } from '@/features/subscription/subscription-required';
import { useSubscription } from '@/features/subscription/use-subscription';
import { isBillingEnabled, isEnabled } from '@/lib/feature-flags';

/**
 * Gates a premium feature's route on an active subscription for the current
 * league (freemium model, FE-021/FE-026). No production route uses it yet — it is
 * retained infrastructure for the first real premium feature; wrap a route with
 * `featureFlag="paywall_<feature>"` to gate it.
 *
 * Reads the current league's subscription state via {@link useSubscription},
 * which bypasses demo mode and the "no league connected" case (reporting active)
 * and treats a failed `getLeague` as active so the page still renders (the API
 * gate applies independently). While the status loads — or while a subscription
 * is activating after returning from Checkout (FE-022) — it shows a spinner;
 * otherwise it shows the inline paywall when the subscription is expired/absent.
 *
 * When the `billing` master flag is off the whole premium section is **hidden**
 * (renders nothing) rather than shown for free (FE-026): with the subscription
 * system disabled there is no way to pay for it, so a premium feature must not
 * leak out unpaywalled. Callers that render their own section header around the
 * guard should gate it on {@link isBillingEnabled} too so they don't leave an
 * orphan header above the hidden section.
 */
export function SubscriptionGuard({
  children,
  featureFlag,
  featureLabel,
}: {
  children: React.ReactNode;
  featureFlag: string;
  featureLabel?: string;
}) {
  // Billing master flag off: premium features don't exist yet — hide the section
  // entirely rather than render it for free (FE-026).
  if (!isBillingEnabled()) return null;
  // Billing is on but this feature isn't flagged premium: render it free, with no
  // paywall and no subscription polling in {@link useSubscription}.
  if (!isEnabled(featureFlag)) return <>{children}</>;
  return (
    <SubscriptionGate featureLabel={featureLabel}>{children}</SubscriptionGate>
  );
}

function SubscriptionGate({
  children,
  featureLabel,
}: {
  children: React.ReactNode;
  featureLabel?: string;
}) {
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
    return (
      <SubscriptionRequired
        activationFailed={activationFailed}
        featureLabel={featureLabel}
      />
    );

  return <>{children}</>;
}
