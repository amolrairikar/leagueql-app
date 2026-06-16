# FE-026: Feature Flags (OpenFeature + SSM Parameter Store)

## Description
Provides a vendor-neutral feature-flag layer for the frontend using
[OpenFeature](https://openfeature.dev/) (`@openfeature/web-sdk`). Flag state is the source-of-truth
in an **AWS SSM Parameter Store** parameter (global, per environment) and is resolved at **runtime**
from the backend's public `GET /feature-flags` endpoint
([BE-017](../backend/BE-017-feature-flags.md)) — so a console toggle reaches the SPA **without a
rebuild**. There is **no bundled config**: the app fetches the
flags at bootstrap and fails safe to `false` for every flag until they resolve (and any time the
backend is unreachable). Evaluation goes through OpenFeature's in-memory provider so call sites
depend only on the neutral helper (`isEnabled` / `isBillingEnabled` from `@/lib/feature-flags`).

A `billing` **master** flag gates all subscription UI
([FE-021](FE-021-subscription-access-control.md),
[FE-022](FE-022-subscription-checkout.md),
[FE-023](FE-023-subscription-management.md)) and the billing guidance in the user guide
([FE-016](FE-016-instructions-docs-page.md)). It defaults **OFF** (fail-safe). When OFF:
- `SubscriptionGuard` **hides** the premium section entirely (renders nothing) — with the
  subscription system disabled there is no way to pay for it, so a premium feature must not leak
  out unpaywalled. The `useSubscription` polling is likewise skipped (the gate never mounts the
  subscription logic). A caller that renders its own section header around the guard gates that
  header on `isBillingEnabled` too, so the section disappears as a whole rather than leaving an
  orphan label.
- The owner-only "Manage Subscription" sidebar entry and its `ManageSubscriptionDialog` are
  hidden (the `useSubscription` "expiring soon" poll behind them does not run).
- The `/docs` user guide hides its Subscribing, Free Trial, and Managing Billing sections (and
  their TOC entries), the subscription FAQ, and inline billing mentions.

On top of the master flag, the **`premium_feature`** flag implements the freemium model
([FE-021](FE-021-subscription-access-control.md)). With `billing` ON, a premium section's
`SubscriptionGuard` paywalls when `premium_feature` is **ON** and renders the feature free when it
is **OFF** (rolled out, not yet paywalled). With `billing` OFF the section is hidden regardless of
`premium_feature`. Every premium feature shares this one flag. The schedule-swap simulator
([FE-031](FE-031-schedule-swap-simulator.md)) is the first section wrapped with it.

The backend resolves the same flags from the same SSM source and is the real enforcement
boundary ([BE-014](../backend/BE-014-subscription-access-control.md)), so even with the UI flag
momentarily stale the API gate still governs access.

## Resolution & reactivity
- `initFeatureFlags()` runs once at bootstrap (`app/main.tsx`, before first paint), fetching
  `${API_BASE_URL}/feature-flags` (bare `fetch`, no auth) and building the `InMemoryProvider` from
  the response. It is a **no-op under Vitest** so component tests never hit the network.
- A light refresh (a poll interval + a refresh on `visibilitychange`) re-fetches the flags so a
  console toggle is picked up without a reload; on a change it swaps the provider, which emits
  `PROVIDER_READY` / `PROVIDER_CONFIGURATION_CHANGED`.
- `FeatureFlagProvider` (`app/feature-flags-provider.tsx`, wrapping `<App />`) listens for those
  events and **remounts the subtree** (via a changing `key`) so the synchronous `isEnabled()` call
  sites — which take no flag props — re-evaluate. The initial (already-applied) flags are skipped,
  so the app remounts only on a genuine later change (a rare operator action).
- **Fail-safe:** a non-200, network error, or unreachable backend leaves the current (or initial
  all-off) provider in place — a transient outage never flips a flag on.

## Scope
- Module: `frontend/src/lib/feature-flags.ts` — registers an all-off `InMemoryProvider` at load,
  exposes `isEnabled(name)` / `isBillingEnabled()`, `initFeatureFlags()` (fetch + refresh), and
  `refreshFlags()` (the mapping seam). A test-only `setFlagsForTesting({...})` swaps the active
  flag map.
- Source: the public `GET /feature-flags` endpoint (BE-017), resolved from AWS SSM Parameter Store.
  No checked-in JSON.
- Call sites (unchanged):
  - `frontend/src/features/subscription/subscription-guard.tsx` — `SubscriptionGuard` takes a
    `featureFlag` prop and renders **nothing** when billing is off; with billing on it returns its
    children directly when the named feature flag is off, otherwise renders the inner
    `SubscriptionGate` that runs `useSubscription`. The schedule-swap simulator (FE-031) wraps it
    with `featureFlag="premium_feature"` and gates its own section header on `isBillingEnabled`.
  - `frontend/src/features/sidebar/app-sidebar.tsx` — the "Manage Subscription" item and
    `ManageSubscriptionDialog` render only when billing is on.
  - `frontend/src/features/instructions/instructions-page.tsx` — filters the billing TOC entries
    and FAQ and conditionally renders the billing sections / inline mentions.
  - `frontend/src/features/landing_page/landing-page.tsx`.
- Dependency: `@openfeature/web-sdk` (`frontend/package.json`). No new packages, no CSP change —
  `api.leagueql.com` (and the dev API origin) are already allowed by `connect-src`
  ([FE-024](FE-024-security-headers.md)).

## Edge Cases
- **Flags not yet resolved / backend unreachable:** every flag reads `false` (feature off).
- **Unknown flag name / spec without `enabled`:** `isEnabled` returns the `false` default.
- **Runtime toggle mid-session:** the refresh swaps the provider and the app remounts so the UI
  reflects the new flags; this is a soft re-render of the tree (current route preserved).
- **UI/API flag mismatch (brief):** harmless — the backend gate
  ([BE-014](../backend/BE-014-subscription-access-control.md)) is the source of truth; the UI flag
  only controls what is shown.

## Acceptance Criteria
- [ ] With `billing` OFF (default / fail-safe), every premium section (the guard's content and
      any caller-rendered section header) is hidden — never rendered for free — and no
      subscription spinner shows.
- [ ] With `billing` OFF, the sidebar shows no "Manage Subscription" entry and the dialog is
      not mounted.
- [ ] With `billing` OFF, the `/docs` user guide hides the Subscribing, Free Trial, and
      Managing Billing sections while still rendering the rest of the guide.
- [ ] With `billing` OFF, no `getLeague`-driven subscription poll runs for the guard or sidebar.
- [ ] `premium_feature` is the shared flag every premium feature gates on; the schedule-swap
      simulator (FE-031) is wrapped with it.
- [ ] An unknown flag evaluates to `false`.
- [ ] Editing the feature-flag parameter value in the SSM console changes the UI within the refresh
      window **without a rebuild**.
- [ ] `initFeatureFlags()` is a no-op under Vitest (no `/feature-flags` fetch in component tests).

## Sources
`frontend/src/lib/feature-flags.ts`, `frontend/src/app/feature-flags-provider.tsx`,
`frontend/src/app/main.tsx`, `frontend/src/app/clerk-with-theme.tsx`,
`frontend/src/features/subscription/subscription-guard.tsx`,
`frontend/src/features/sidebar/app-sidebar.tsx`,
[BE-017](../backend/BE-017-feature-flags.md) (backend source + `GET /feature-flags`).
