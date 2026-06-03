import { Lock } from 'lucide-react';

import { Spinner } from '@/components/spinner';
import { Button } from '@/components/ui/button';
import { useStripeBilling } from '@/features/subscription/use-stripe-billing';
import { getLeagueCookies } from '@/lib/cookie-handler';

/**
 * Inline paywall shown in place of an analytics page when the current league's
 * subscription is expired or absent. Rendered inside the app layout so the
 * sidebar and header stay visible. The single primary action starts Stripe
 * Checkout (FE-022).
 */
export function SubscriptionRequired() {
  const { startCheckout, checkoutLoading } = useStripeBilling();
  const { leagueId, platform } = getLeagueCookies();

  return (
    <div className="flex min-h-[70vh] flex-col items-center justify-center gap-4 p-8 text-center">
      <div className="bg-muted flex size-12 items-center justify-center rounded-full">
        <Lock className="size-6 text-muted-foreground" />
      </div>
      <h1 className="text-2xl font-bold">Subscription required</h1>
      <p className="text-muted-foreground max-w-md">
        This league&apos;s subscription has expired. Subscribe to regain access
        to your league&apos;s analytics.
      </p>
      <Button
        className="cursor-pointer"
        disabled={checkoutLoading || !leagueId}
        onClick={() => void startCheckout(leagueId, platform)}
      >
        {checkoutLoading && <Spinner className="size-4" />}
        Subscribe
      </Button>
    </div>
  );
}
