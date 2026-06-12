import { Lock } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

import { Spinner } from '@/components/spinner';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { useIsOwner } from '@/features/ownership/use-is-owner';
import { useStripeBilling } from '@/features/subscription/use-stripe-billing';
import { getLeagueCookies } from '@/lib/cookie-handler';
import { ErrorAlert } from '@/lib/error-alert';

/**
 * Inline paywall shown in place of a premium feature when the current league's
 * subscription is expired or absent (freemium model, FE-021). The single primary
 * action starts Stripe Checkout (FE-022).
 *
 * `featureLabel` names the gated premium feature (e.g. "League migration") so the
 * copy is feature-specific; when omitted the generic "Subscription required" copy
 * is shown.
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
  const navigate = useNavigate();

  return (
    <div className="flex flex-1 flex-col items-center justify-center gap-4 p-8 text-center">
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
      <h1 className="text-2xl font-bold">
        {featureLabel
          ? `${featureLabel} is a premium feature`
          : 'Subscription required'}
      </h1>
      {isOwner ? (
        <>
          <p className="text-muted-foreground max-w-md">
            {featureLabel
              ? `Subscribe to unlock ${featureLabel.toLowerCase()} for your league.`
              : "Subscribe to gain access to your league's analytics."}
          </p>
          <Button
            className="cursor-pointer"
            disabled={checkoutLoading || !leagueId}
            onClick={() => void startCheckout(leagueId, platform)}
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
      {/* Always offer a way out for a user who does not want to subscribe. */}
      <Button
        variant="ghost"
        className="cursor-pointer"
        onClick={() => void navigate('/home')}
      >
        Back to dashboard
      </Button>
    </div>
  );
}
