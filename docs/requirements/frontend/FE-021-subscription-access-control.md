# FE-021: Subscription Access Control

> **Per-feature paywall, feature-flagged ([FE-026](FE-026-feature-flags.md)).** LeagueQL is
> **freemium**: the app is free except for **premium features**. A `SubscriptionGuard` gates a
> route only when **both** the `billing` master flag **and** that route's per-feature flag are ON.
> **No route is wrapped today** — the guard is retained infrastructure, and a placeholder
> `paywall_test_feature` flag plus the paywall UI keep the mechanism ready for the first real
> premium feature. When `billing` is OFF (the current default) the guard is a pass-through.

## Description
Provides the `SubscriptionGuard` used to gate a **premium** route on an active subscription, plus
the "Manage Subscription" sidebar entry point. **No production route is currently wrapped** (the
analytics pages and the Migrate League wizard are all free); the guard is kept ready for a future
premium feature. When wrapped, the guard reads the current league's `subscription_end_time` (from
`GET /leagues/{id}` via the existing `getLeague` accessor) and, when the subscription is expired
or absent, replaces the page content with an inline, feature-specific paywall while keeping the
header visible. The sidebar's former "Request a Feature" item is replaced with a "Manage
Subscription" item that opens the subscription dialog (shown only when `billing` is on).
This feature owns the dialog **shell** and the gating; the dialog's real billing content is
provided by checkout ([FE-022](FE-022-subscription-checkout.md)) and the billing portal
([FE-023](FE-023-subscription-management.md)). When the current league's subscription is active
but lapses within `SUBSCRIPTION_EXPIRY_WARNING_DAYS` (14) days, a red alert dot is overlaid on
the item's icon as an early-renewal nudge. Backend enforcement is covered by
[BE-014](../backend/BE-014-subscription-access-control.md).

The guard and the sidebar dot both read subscription state through one shared hook,
`useSubscription` (`frontend/src/features/subscription/use-subscription.ts`), so they fetch the
current league's `subscription_end_time` through a single path with identical bypass/error
handling.

## Scope
- Shared hook: `frontend/src/features/subscription/use-subscription.ts` — reads the current
  league's `subscription_end_time` via `getLeague()` (`src/components/api/leagues.ts`) using
  `getLeagueCookies()` for `leagueId`/`platform`, and derives `loading` / `isActive` /
  `expiringSoon`.
- Guard: `frontend/src/features/subscription/subscription-guard.tsx` takes a `featureFlag` (and
  optional `featureLabel`) prop; it is a pass-through when `billing` is off **or** the named flag
  is off, otherwise it consumes `useSubscription` and renders the paywall when expired. **No
  production route renders it yet** — wrap a future premium route with
  `featureFlag="paywall_<feature>"` to gate it. Exercised by component tests in isolation.
- Paywall: `frontend/src/features/subscription/subscription-required.tsx` (inline) with
  feature-specific copy (driven by the optional `featureLabel`), a primary **Subscribe** button
  that starts checkout ([FE-022](FE-022-subscription-checkout.md)) for the owner, and a secondary
  **Back to dashboard** action (shown to everyone) that navigates to `/home` so a user who does
  not want to pay can leave the gated feature.
- Dialog: `frontend/src/features/subscription/manage-subscription-dialog.tsx` (skeleton).
- Sidebar: `frontend/src/features/sidebar/app-sidebar.tsx` — "Manage Subscription" item plus the
  expiring-soon alert dot.

## Edge Cases
- **No route wrapped today:** no page is paywalled regardless of flag state — the guard is not
  rendered by any production route.
- **Billing master flag OFF (current default):** when a route *is* wrapped, the guard is a
  pass-through everywhere.
- **Premium feature flag OFF:** even with `billing` ON, the guard is a pass-through for that
  feature (e.g. `paywall_test_feature` off ⇒ the wrapped page is free).
- **Loading (wrapped, both flags ON):** while `getLeague` resolves, show a spinner rather than
  the paywall.
- **`subscription_end_time` absent or in the past (wrapped, both flags ON):** show the paywall
  (treated as expired).
- **`subscription_end_time` in the future:** render the page normally.
- **Demo mode:** the guard bypasses entirely (no subscription concept in demo).
- **No league connected:** behaves like the rest of the app when cookies are empty (the
  guard does not crash on a missing league).
- **Manage Subscription dialog:** opens/closes; its billing content (Subscribe / Manage billing)
  is defined by [FE-022](FE-022-subscription-checkout.md) and
  [FE-023](FE-023-subscription-management.md).
- **Expiring-soon dot:** shown only when the subscription is active *and* `subscription_end_time`
  is within `SUBSCRIPTION_EXPIRY_WARNING_DAYS` (14) days. An expired subscription shows the paywall
  (not the dot); a subscription expiring further out shows neither.
- **Dot visibility while collapsed:** the dot is overlaid on the icon (not the hidden label), so it
  remains visible when the sidebar is collapsed to icons.
- **Dot during load / error / demo / no league:** the dot is hidden (the hook reports active and
  non-expiring in the bypass and error cases, and `expiringSoon` is false while loading).

## Acceptance Criteria
- [ ] No production route is paywalled today (the guard is not rendered by any route).
- [ ] When a route is wrapped with both `billing` and its `paywall_*` flag ON, it shows the inline
      paywall when the subscription is expired or `subscription_end_time` is absent, and renders
      normally when it is in the future.
- [ ] When a route is wrapped, the guard is a pass-through if `billing` is OFF **or** the named
      per-feature flag is OFF.
- [ ] A spinner is shown while the subscription state is loading on a paywalled (wrapped) route.
- [ ] The paywall shows a "Back to dashboard" action (to both owner and non-owner) that navigates
      to `/home`, so a user who does not want to subscribe can leave the gated feature.
- [ ] Demo mode bypasses the subscription gate.
- [ ] The sidebar shows "Manage Subscription" (replacing "Request a Feature") and clicking it
      opens the subscription dialog.
- [ ] A red alert dot appears on the "Manage Subscription" icon when the current league's
      subscription is active but expires within 14 days, and is hidden otherwise (active >14 days
      out, expired, loading, demo mode, or no league).

## Authorization (FE-025)
Only the league owner sees the Subscribe CTA on the paywall; a non-owner sees an "ask the league owner to subscribe" message ([FE-025](FE-025-ownership-transfer-owner-gated-actions.md)).

## Sources
`src/features/subscription/`, `src/app/app.tsx`, `src/features/sidebar/app-sidebar.tsx`,
`src/components/api/leagues.ts`, `src/components/api/types.ts`.
