import { Sparkles } from 'lucide-react';

import { Spinner } from '@/components/spinner';
import { Badge } from '@/components/ui/badge';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip';
import { SubscriptionRequired } from '@/features/subscription/subscription-required';
import { useSubscription } from '@/features/subscription/use-subscription';
import { isDemoMode } from '@/lib/cookie-handler';
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
 *
 * In **demo mode** there is no league and no subscription concept, so the gate
 * would render the feature unlocked. Rather than leave demo visitors thinking the
 * feature is free, we still render it (so they can explore) but mark it with a
 * "Premium" badge explaining it needs a subscription on a real league (FE-015).
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
  // Demo mode has no subscription to check; show the feature but label it premium
  // so demo visitors aren't misled into thinking it's free (FE-015).
  if (isDemoMode())
    return (
      <>
        <DemoPremiumBadge featureLabel={featureLabel} />
        {children}
      </>
    );
  return (
    <SubscriptionGate featureLabel={featureLabel}>{children}</SubscriptionGate>
  );
}

/**
 * Small "Premium" pill shown above a premium feature in demo mode, with a tooltip
 * explaining the feature is unlocked for exploration but needs a subscription on a
 * real league.
 */
function DemoPremiumBadge({ featureLabel }: { featureLabel?: string }) {
  const subject = featureLabel ?? 'This';
  return (
    <TooltipProvider>
      <Tooltip>
        <TooltipTrigger asChild>
          <Badge variant="secondary" className="mb-2.5 cursor-default">
            <Sparkles />
            Premium
          </Badge>
        </TooltipTrigger>
        <TooltipContent
          side="top"
          className="max-w-64 text-center leading-relaxed bg-popover text-popover-foreground border border-border shadow-md [&>svg]:fill-popover [&>svg]:bg-popover"
        >
          {subject} is a premium feature, unlocked here so you can explore it in
          the demo. With your own league it requires a subscription.
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
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
