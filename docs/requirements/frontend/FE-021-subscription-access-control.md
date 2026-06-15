# FE-021: Subscription Access Control

> **Premium paywall, feature-flagged ([FE-026](FE-026-feature-flags.md)).** LeagueQL is
> **freemium**: the app is free except for **premium features**. A `SubscriptionGuard` gates a
> premium section only when **both** the `billing` master flag **and** the shared `premium_feature`
> flag are ON. The schedule-swap simulator ([FE-031](FE-031-schedule-swap-simulator.md)) is the
> first wrapped premium section; every premium feature shares the `premium_feature` flag and is
> gated identically. When `billing` is OFF (the current default) the guard hides the section
> entirely; with `billing` ON but `premium_feature` OFF the guard renders the section for free.

## Description
Provides the `SubscriptionGuard` used to gate a **premium** route on an active subscription, plus
the "Manage Subscription" sidebar entry point. The schedule-swap simulator
([FE-031](FE-031-schedule-swap-simulator.md)) is the first wrapped premium section; the analytics
pages and the Migrate League wizard remain free. When wrapped, the guard reads the current
league's `subscription_end_time` (from
`GET /leagues/{id}` via the existing `getLeague` accessor) and, when the subscription is expired
or absent, replaces the gated section with a **blurred lock overlay** — a non-interactive,
blurred skeleton behind a lock icon and a feature-specific Subscribe CTA. Because the gated
component is swapped out (never mounted), the premium feature's own data is **not fetched** while
it is locked; the rest of the page keeps loading. The sidebar's former "Request a Feature" item is replaced with a "Manage
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
  optional `featureLabel`) prop; it renders nothing when `billing` is off, is a pass-through when
  `billing` is on but the named flag is off, otherwise it consumes `useSubscription` and renders
  the locked overlay when expired
  **instead of** the gated children (so the premium feature is never mounted and its data is not
  fetched). The schedule-swap simulator (FE-031) renders it with `featureFlag="premium_feature"`;
  every premium section uses the same shared flag. Also exercised by component tests in isolation.
- Locked overlay: `frontend/src/features/subscription/subscription-required.tsx` — a blurred,
  non-interactive skeleton behind a lock icon with feature-specific copy (driven by the optional
  `featureLabel`) and a primary **Subscribe** button that starts checkout
  ([FE-022](FE-022-subscription-checkout.md)) for the owner (a non-owner sees an "ask the league
  owner" message instead). There is no full-page takeover and no "Back to dashboard" action — the
  rest of the page stays usable around the locked section.
- Dialog: `frontend/src/features/subscription/manage-subscription-dialog.tsx` (skeleton).
- Sidebar: `frontend/src/features/sidebar/app-sidebar.tsx` — "Manage Subscription" item plus the
  expiring-soon alert dot.

## Edge Cases
- **Schedule-swap wrapped (FE-031):** the simulator is paywalled only when both flags are ON; with
  `billing` OFF the section (including its header) is hidden, and with `billing` ON but
  `premium_feature` OFF it renders for everyone.
- **Billing master flag OFF (current default):** the guard renders nothing everywhere a section is
  wrapped; the wrapped section is hidden rather than shown for free (a caller's own section header
  is gated on `isBillingEnabled` too, so nothing is left orphaned).
- **Premium feature flag OFF:** with `billing` ON, the guard is a pass-through (e.g.
  `premium_feature` off ⇒ the wrapped section is free).
- **Loading (wrapped, both flags ON):** while `getLeague` resolves, show a spinner rather than
  the locked overlay (the gated component stays unmounted, so it does not fetch).
- **`subscription_end_time` absent or in the past (wrapped, both flags ON):** show the locked
  overlay (treated as expired); the gated feature's data is not fetched.
- **`subscription_end_time` in the future:** render the gated component normally.
- **Demo mode:** the guard bypasses entirely (no subscription concept in demo).
- **No league connected:** behaves like the rest of the app when cookies are empty (the
  guard does not crash on a missing league).
- **Manage Subscription dialog:** opens/closes; its billing content (Subscribe / Manage billing)
  is defined by [FE-022](FE-022-subscription-checkout.md) and
  [FE-023](FE-023-subscription-management.md).
- **Expiring-soon dot:** shown only when the subscription is active *and* `subscription_end_time`
  is within `SUBSCRIPTION_EXPIRY_WARNING_DAYS` (14) days. An expired subscription shows the locked
  overlay (not the dot); a subscription expiring further out shows neither.
- **Dot visibility while collapsed:** the dot is overlaid on the icon (not the hidden label), so it
  remains visible when the sidebar is collapsed to icons.
- **Dot during load / error / demo / no league:** the dot is hidden (the hook reports active and
  non-expiring in the bypass and error cases, and `expiringSoon` is false while loading).

## Acceptance Criteria
- [ ] The schedule-swap simulator (FE-031) is paywalled only when both `billing` and
      `premium_feature` are ON; with `billing` OFF the section (and its header) is hidden, and with
      `billing` ON but `premium_feature` OFF it renders for everyone.
- [ ] When a section is wrapped with both `billing` and `premium_feature` ON, it shows the blurred
      lock overlay when the subscription is expired or `subscription_end_time` is absent, and
      renders the gated component normally when it is in the future.
- [ ] While locked, the gated component is not mounted and its data is not fetched (only the rest
      of the page loads); the overlay shows a Subscribe CTA to the owner and an "ask the league
      owner" message to a non-owner.
- [ ] When a section is wrapped, the guard renders nothing if `billing` is OFF, and is a
      pass-through if `billing` is ON but `premium_feature` is OFF.
- [ ] A spinner is shown while the subscription state is loading on a paywalled (wrapped) section.
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
