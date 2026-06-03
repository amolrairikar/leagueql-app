import { Lock } from 'lucide-react';

import { Spinner } from '@/components/spinner';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { useStripeBilling } from '@/features/subscription/use-stripe-billing';
import { getLeagueCookies } from '@/lib/cookie-handler';
import { ErrorAlert } from '@/lib/error-alert';

/**
 * Inline paywall shown in place of an analytics page when the current league's
 * subscription is expired or absent. Rendered inside the app layout so the
 * sidebar and header stay visible. The single primary action starts Stripe
 * Checkout (FE-022).
 *
 * `activationFailed` is set when the user returned from Checkout but the
 * subscription never activated within the poll window (e.g. a webhook problem),
 * so they aren't left at a silent paywall after paying.
 */
export function SubscriptionRequired({
  activationFailed,
}: {
  activationFailed?: boolean;
}) {
  const { startCheckout, checkoutLoading, error } = useStripeBilling();
  const { leagueId, platform } = getLeagueCookies();

  return (
    <div className="flex min-h-[70vh] flex-col items-center justify-center gap-4 p-8 text-center">
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
      {error && <ErrorAlert message={error} className="max-w-md text-left" />}
    </div>
  );
}
