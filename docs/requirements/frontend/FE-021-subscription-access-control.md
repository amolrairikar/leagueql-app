# FE-021: Subscription Access Control

## Description
Gates the in-app analytics pages on an active subscription and exposes a "Manage Subscription"
entry point. The ten `AppLayout` analytics routes are wrapped in a `SubscriptionGuard` that
reads the current league's `subscription_end_time` (from `GET /leagues/{id}` via the existing
`getLeague` accessor) and, when the subscription is expired or absent, replaces the page content
with an inline "Subscription required" paywall while keeping the sidebar and header visible.
The sidebar's former "Request a Feature" item is replaced with a "Manage Subscription" item that
opens a (currently skeleton) subscription dialog — the real Clerk/Stripe billing UI is a later
task. Backend enforcement is covered by [BE-014](../backend/BE-014-subscription-access-control.md).

## Scope
- Guard: `frontend/src/features/subscription/subscription-guard.tsx` wraps `AppLayout` children
  in `src/app/app.tsx`. Uses `getLeagueCookies()` for the current `leagueId`/`platform` and
  `getLeague()` (`src/components/api/leagues.ts`) for `subscription_end_time`.
- Paywall: `frontend/src/features/subscription/subscription-required.tsx` (inline, rendered
  inside the app layout) with a button that opens the manage dialog.
- Dialog: `frontend/src/features/subscription/manage-subscription-dialog.tsx` (skeleton).
- Sidebar: `frontend/src/features/sidebar/app-sidebar.tsx` — "Manage Subscription" item.

## Edge Cases
- **Loading:** while `getLeague` resolves, show a spinner rather than the paywall.
- **`subscription_end_time` absent or in the past:** show the paywall (treated as expired).
- **`subscription_end_time` in the future:** render the page normally.
- **Demo mode:** the guard bypasses entirely (no subscription concept in demo).
- **No league connected:** behaves like the rest of the app when cookies are empty (the
  guard does not crash on a missing league).
- **Manage Subscription dialog:** opens/closes; content is a placeholder skeleton for now.

## Acceptance Criteria
- [ ] Analytics routes show the inline paywall when the current league's subscription is
      expired or its `subscription_end_time` is absent.
- [ ] Analytics routes render normally when `subscription_end_time` is in the future.
- [ ] A spinner is shown while the subscription state is loading.
- [ ] Demo mode bypasses the subscription gate.
- [ ] The sidebar shows "Manage Subscription" (replacing "Request a Feature") and clicking it
      opens the subscription dialog.

## Sources
`src/features/subscription/`, `src/app/app.tsx`, `src/features/sidebar/app-sidebar.tsx`,
`src/components/api/leagues.ts`, `src/components/api/types.ts`.
