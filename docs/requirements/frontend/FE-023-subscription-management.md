# FE-023: Subscription Management (Billing Portal)

> **Feature-flagged ([FE-026](FE-026-feature-flags.md)).** Subscription management is shown only
> when the `billing` flag is ON. When OFF (the current default), the "Manage Subscription"
> sidebar entry and its dialog are hidden, and the backend billing-portal endpoint returns `404`.

## Description
Turns the skeleton Manage Subscription dialog ([FE-021](FE-021-subscription-access-control.md))
into a real management surface backed by Stripe's Billing Portal. For a user with an existing
Stripe customer, the dialog offers **Manage billing**, which calls `POST /billing-portal-session`
and redirects to the Stripe-hosted portal where the user can update their card or cancel
(cancellation takes effect **immediately** per [BE-015](../backend/BE-015-stripe-billing.md)).

The dialog reflects the current subscription state via `useSubscription` (active with a
renewal/expiry date, expiring-soon, or expired) and routes users with no subscription to the
Subscribe / checkout flow ([FE-022](FE-022-subscription-checkout.md)) instead of Manage billing.
On return from the portal, subscription state is refreshed with the cache bypassed so an immediate
cancellation surfaces the paywall right away.

## Scope
- **API accessor:** `createBillingPortalSession()` in the billing client module
  (`src/components/api/billing.ts`), POSTing to `/billing-portal-session` and returning
  `{ data: { url } }` (auth via the `__session` cookie).
- **Dialog content:** `manage-subscription-dialog.tsx` shows the subscription status from
  `useSubscription` and the appropriate primary action — **Manage billing** (portal) when a Stripe
  customer exists, otherwise **Subscribe** ([FE-022]).
- **Manage trigger:** on "Manage billing" → call the accessor → `window.location.assign(url)`.
- **Return destination:** the portal's "Return to LeagueQL" button (`return_url`) lands the user
  on the in-app **dashboard home** (`/home`).
- **Return handling:** refresh subscription state on return (`clearApiCache()`), so an immediate
  cancellation flips gated pages to the paywall.
- **No-customer routing:** a `404` from the portal endpoint (no Stripe customer yet) presents the
  Subscribe action instead of Manage billing.

## Edge Cases
- **404 (no billing account):** the user has never subscribed → show Subscribe, not Manage billing.
- **Demo mode:** the dialog shows a non-billing placeholder / disabled state (no subscription
  concept in demo).
- **Active subscription:** show the renewal/expiry date; expiring-soon styling is consistent with
  the sidebar alert dot ([FE-021]).
- **In-flight state:** the Manage billing button shows a loading state while the portal session is
  created and is disabled meanwhile.
- **Error creating the portal session:** the error message from the rejected request is held in
  `useStripeBilling` and shown inline (an `ErrorAlert`) inside the dialog; the button returns to
  idle. A `404` is the exception — it triggers the Subscribe fallback rather than showing an error.
- **Return after immediate cancellation:** the refreshed state reads expired, so gated pages show
  the paywall on the next render.
- **Mobile — opening from the sidebar:** on mobile the sidebar is a slide-over sheet; selecting
  "Manage Subscription" closes that sheet and opens the dialog. The dialog must stay open — it is
  rendered outside the sidebar's sheet subtree so closing the sheet does not unmount it.

## Acceptance Criteria
- [ ] The Manage Subscription dialog shows the current subscription status (active with date,
      expiring-soon, or expired).
- [ ] When a Stripe customer exists, "Manage billing" calls `POST /billing-portal-session` and
      redirects to the returned URL.
- [ ] A `404` (no billing account) shows the Subscribe action ([FE-022]) instead of Manage billing.
- [ ] On return from the portal, subscription state is refreshed so an immediate cancellation
      surfaces the paywall.
- [ ] The Manage billing button shows a loading state and returns to idle on error, with a
      non-404 failure shown inline (an `ErrorAlert`) in the dialog.
- [ ] Demo mode shows a non-billing placeholder.
- [ ] On mobile, opening the dialog from the sidebar closes the sidebar sheet but the dialog stays
      open (it is not unmounted with the sheet).

## Sources
`src/components/api/billing.ts` (new), `src/features/subscription/manage-subscription-dialog.tsx`,
`src/features/subscription/use-subscription.ts`,
`src/features/subscription/use-stripe-billing.ts`, `src/features/sidebar/app-sidebar.tsx`,
`src/lib/error-alert.tsx`, `src/lib/api-client.ts`,
[BE-015](../backend/BE-015-stripe-billing.md),
[FE-021](FE-021-subscription-access-control.md), [FE-022](FE-022-subscription-checkout.md).
