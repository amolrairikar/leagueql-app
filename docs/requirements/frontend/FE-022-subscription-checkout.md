# FE-022: Subscription Checkout (Making Payments)

> **Feature-flagged ([FE-026](FE-026-feature-flags.md)).** Checkout is reachable only when the
> `billing` flag is ON. When OFF (the current default), the paywall and "Manage Subscription"
> entry points that start checkout are hidden, and the backend checkout endpoint returns `404`.

## Description
Lets a user start a paid subscription for the current league via Stripe Checkout. A **Subscribe**
action — surfaced from the inline paywall ([FE-021](FE-021-subscription-access-control.md)) and
from the Manage Subscription dialog ([FE-023](FE-023-subscription-management.md)) when the league
has no active subscription — calls `POST /leagues/{leagueId}/checkout-session`, then redirects the
browser to the returned Stripe-hosted Checkout URL.

After paying, Stripe returns the user to the app. Because the backend records access
**asynchronously** via the Stripe webhook ([BE-015](../backend/BE-015-stripe-billing.md)), the
freshly-written `subscription_end_time` may not be readable the instant the user lands. On return
the app therefore refreshes subscription state with the cache bypassed and shows a brief
"activating" state, polling for a bounded interval before falling back to the paywall.

## Scope
- **API accessor:** `createCheckoutSession(leagueId, platform, plan, returnPath?)` in a new billing
  client module (`src/components/api/billing.ts`), POSTing to
  `/leagues/{leagueId}/checkout-session?platform=…&plan=…&returnPath=…` and returning
  `{ data: { url } }`. The `returnPath` is the in-app path checkout was started from, used to build
  **both** the Checkout `success_url` and cancel ("back") `cancel_url`. The
  `plan` is `MONTHLY` or `YEARLY` (BE-015 selects the matching Stripe price). Uses `apiClient.post`
  (auth via the `__session` cookie; POSTs are not cached).
- **Plan picker:** a monthly/yearly **toggle** (`plan-toggle.tsx`) rendered above the Subscribe
  CTA, defaulting to `MONTHLY`. Each option shows its price (`$2.99/mo`, `$14.99/yr`) alongside the
  cadence label for full price transparency before checkout, with the yearly option also carrying
  the `Save ~58%` hint; the prices match the landing-page pricing table
  ([FE-001](FE-001-landing-page.md)). Both plans unlock the same premium features; the toggle only
  chooses the billing cadence sent to checkout. Existing subscribers switch plans via the Stripe
  Billing Portal ([FE-023](FE-023-subscription-management.md)).
- **Subscribe trigger:** a "Subscribe" button in `subscription-required.tsx` (the locked overlay)
  and in the Manage Subscription dialog when the subscription is not active. On click → call the
  accessor with the toggled `plan` → `window.location.assign(url)`.
- **Return destination:** both the Stripe `success_url` and `cancel_url` return the user to the
  **page they started checkout from**. The accessor sends the current in-app path
  (`window.location.pathname + search`) as a `returnPath` query param, and BE-015 builds both URLs
  from it (falling back to `/home` when absent or not a safe same-origin relative path). The
  `success_url` carries `?checkout=success` (merged with any existing query) so the return triggers
  the activation poll; the `cancel_url` has no param, so a cancel never polls.
- **Return handling:** the activation poll is driven by the `?checkout=success` query param
  (consumed and stripped via `history.replaceState`), **not** a sessionStorage flag — so a cancel
  return never polls or shows a failure notice. On a success return, refresh subscription state —
  `clearApiCache()` (or read `getLeague` with `skipCache`) so the webhook-written
  `subscription_end_time` is read, with a short bounded poll / "activating" state to absorb
  webhook lag. If the poll window
  elapses without the subscription activating (`activationFailed`), the paywall shows a
  "couldn't confirm your subscription" notice rather than reverting silently.
- **In-flight state:** the Subscribe button shows a loading state and is disabled while the
  session is being created.
- **Types:** a `BillingSessionResponse` (`{ detail, data: { url } }`) in
  `src/components/api/types.ts`.

## Edge Cases
- **Demo mode:** no checkout — the Subscribe action is hidden / bypassed (no subscription concept).
- **No league connected:** the Subscribe action is not shown (nothing to subscribe).
- **409 (already subscribed / another user's in-flight checkout):** the backend message is
  surfaced by an inline `ErrorAlert` rendered next to the Subscribe button (the `useStripeBilling`
  hook exposes the error message), the cache is busted to refresh subscription state, and the
  button returns to idle instead of redirecting again. The same user re-attempting their *own*
  checkout does **not** 409 (they re-claim their marker); a 409 from a *different* user's marker
  self-heals once its window lapses ([BE-015](../backend/BE-015-stripe-billing.md)).
- **Network / 5xx creating the session:** the error message from the rejected request is held in
  `useStripeBilling` and shown inline next to the Subscribe button; the button returns to idle so
  the user can retry.
- **Webhook lag on return:** the subscription may not read active immediately; show an
  "activating subscription" state and poll `getLeague` (cache-busted) for a bounded interval
  before falling back to the paywall.
- **User cancels at Stripe (`cancel_url`):** returns to the app unchanged; still expired, so the
  paywall remains.
- **Double-click / rapid retries:** the button disables while in flight; the backend
  `pending_checkout` marker also guards duplicate subscriptions ([BE-015]).

## Acceptance Criteria
- [ ] A "Subscribe" action appears for a league with no active subscription (paywall + dialog) and
      is hidden in demo mode / when no league is connected.
- [ ] A monthly/yearly toggle (default monthly) is shown with the Subscribe action, with each
      option displaying its price (`$2.99/mo`, `$14.99/yr`); clicking Subscribe calls
      `POST /leagues/{id}/checkout-session` with the selected `plan` and redirects to the returned
      Stripe URL.
- [ ] The button shows a loading state while the session is created and returns to idle on error.
- [ ] A `409` response shows an "already active" message and refreshes subscription state instead
      of redirecting.
- [ ] On return from Checkout, the app refreshes subscription state (cache-busted) and shows an
      activating state until the subscription reads active, then renders the page.
- [ ] If activation does not complete within the poll window, the paywall shows a
      "couldn't confirm your subscription" notice instead of reverting silently.
- [ ] Errors creating the session are shown inline (an `ErrorAlert`) next to the Subscribe button
      in the paywall / dialog — there is no global error banner.

## Sources
`src/components/api/billing.ts` (new), `src/components/api/types.ts`,
`src/features/subscription/subscription-required.tsx`,
`src/features/subscription/manage-subscription-dialog.tsx`,
`src/features/subscription/use-subscription.ts`,
`src/features/subscription/use-stripe-billing.ts`, `src/lib/error-alert.tsx`,
`src/lib/api-client.ts`,
[BE-015](../backend/BE-015-stripe-billing.md), [FE-021](FE-021-subscription-access-control.md),
[FE-023](FE-023-subscription-management.md).
