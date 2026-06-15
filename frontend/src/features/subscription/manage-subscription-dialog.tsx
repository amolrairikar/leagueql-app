import { Spinner } from '@/components/spinner';
import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { useStripeBilling } from '@/features/subscription/use-stripe-billing';
import { useSubscription } from '@/features/subscription/use-subscription';
import { ApiError } from '@/lib/api-client';
import { getLeagueCookies, isDemoMode } from '@/lib/cookie-handler';
import { ErrorAlert } from '@/lib/error-alert';

interface ManageSubscriptionDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

function formatDate(iso?: string): string {
  if (!iso) return '';
  const date = new Date(iso);
  return Number.isNaN(date.getTime())
    ? ''
    : date.toLocaleDateString(undefined, {
        year: 'numeric',
        month: 'long',
        day: 'numeric',
      });
}

/**
 * Manage Subscription dialog (FE-023). Shows the current league's subscription
 * status and routes the user to Stripe Checkout (Subscribe — FE-022) or the Stripe
 * Billing Portal (Manage billing), depending on whether a subscription exists. A
 * 404 from the portal (no Stripe customer yet) falls back to Checkout.
 */
export function ManageSubscriptionDialog({
  open,
  onOpenChange,
}: ManageSubscriptionDialogProps) {
  const demoMode = isDemoMode();
  const { leagueId, platform } = getLeagueCookies();
  const { isActive, expiringSoon, endTime } = useSubscription();
  const {
    startCheckout,
    openBillingPortal,
    checkoutLoading,
    portalLoading,
    error,
  } = useStripeBilling();

  // Evidence of an existing Stripe customer: a subscription_end_time has been
  // written for this league at some point. A 404 from the portal corrects this.
  const hasCustomer = Boolean(endTime);

  async function handleManageBilling() {
    try {
      await openBillingPortal();
    } catch (err) {
      if (err instanceof ApiError && err.status === 404) {
        await startCheckout(leagueId, platform);
      }
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle className="text-2xl font-bold">
            Manage Subscription
          </DialogTitle>
        </DialogHeader>

        {demoMode ? (
          <DialogDescription>
            Subscription management is not available in demo mode.
          </DialogDescription>
        ) : isActive ? (
          <>
            <DialogDescription>
              Your subscription is active
              {endTime ? ` and renews on ${formatDate(endTime)}` : ''}.
              {expiringSoon &&
                ' It is expiring soon — update your billing to avoid losing access.'}
            </DialogDescription>
            <DialogFooter>
              <Button
                className="cursor-pointer"
                disabled={portalLoading}
                onClick={() => void handleManageBilling()}
              >
                {portalLoading && <Spinner className="size-4" />}
                Manage billing
              </Button>
            </DialogFooter>
          </>
        ) : (
          <>
            <DialogDescription>
              {hasCustomer
                ? "This league's subscription has expired. Subscribe again to restore access, or update your billing details."
                : 'Subscribe to unlock premium features.'}
            </DialogDescription>
            <DialogFooter>
              <Button
                className="cursor-pointer"
                disabled={checkoutLoading || !leagueId}
                onClick={() => void startCheckout(leagueId, platform)}
              >
                {checkoutLoading && <Spinner className="size-4" />}
                Subscribe
              </Button>
              {hasCustomer && (
                <Button
                  variant="outline"
                  className="cursor-pointer"
                  disabled={portalLoading}
                  onClick={() => void handleManageBilling()}
                >
                  {portalLoading && <Spinner className="size-4" />}
                  Manage billing
                </Button>
              )}
            </DialogFooter>
          </>
        )}

        {error && <ErrorAlert message={error} />}
      </DialogContent>
    </Dialog>
  );
}
