# FE-021: Subscription Access Control

> **Feature-flagged ([FE-026](FE-026-feature-flags.md)).** The paywall is active only when the
> `billing` flag is ON. When OFF (the current default), `SubscriptionGuard` is a pass-through
> and the analytics pages render with no paywall or subscription spinner.

## Description
Gates the in-app analytics pages on an active subscription and exposes a "Manage Subscription"
entry point. The ten `AppLayout` analytics routes are wrapped in a `SubscriptionGuard` that
reads the current league's `subscription_end_time` (from `GET /leagues/{id}` via the existing
`getLeague` accessor) and, when the subscription is expired or absent, replaces the page content
with an inline "Subscription required" paywall while keeping the sidebar and header visible.
The sidebar's former "Request a Feature" item is replaced with a "Manage Subscription" item that
opens the subscription dialog. This feature owns the dialog **shell** and the gating; the dialog's
real billing content is provided by checkout ([FE-022](FE-022-subscription-checkout.md)) and the
billing portal ([FE-023](FE-023-subscription-management.md)). When the current league's
subscription is active but lapses within
`SUBSCRIPTION_EXPIRY_WARNING_DAYS` (14) days, a red alert dot is overlaid on the item's icon as an
early-renewal nudge. Backend enforcement is covered by
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
- Guard: `frontend/src/features/subscription/subscription-guard.tsx` wraps `AppLayout` children
  in `src/app/app.tsx`. Consumes `useSubscription`.
- Paywall: `frontend/src/features/subscription/subscription-required.tsx` (inline, rendered
  inside the app layout) with a single primary **Subscribe** button that starts checkout
  ([FE-022](FE-022-subscription-checkout.md)).
- Dialog: `frontend/src/features/subscription/manage-subscription-dialog.tsx` (skeleton).
- Sidebar: `frontend/src/features/sidebar/app-sidebar.tsx` — "Manage Subscription" item plus the
  expiring-soon alert dot.

## Edge Cases
- **Loading:** while `getLeague` resolves, show a spinner rather than the paywall.
- **`subscription_end_time` absent or in the past:** show the paywall (treated as expired).
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
- [ ] Analytics routes show the inline paywall when the current league's subscription is
      expired or its `subscription_end_time` is absent.
- [ ] Analytics routes render normally when `subscription_end_time` is in the future.
- [ ] A spinner is shown while the subscription state is loading.
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
