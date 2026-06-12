# FE-026: Feature Flags (OpenFeature)

## Description
Provides a vendor-neutral feature-flag layer for the frontend using
[OpenFeature](https://openfeature.dev/) (`@openfeature/web-sdk`). Flag state is read at **build
time** from a checked-in JSON config, `frontend/src/config/feature-flags.json`, that maps each
flag name to `{ "enabled": <bool> }`. The config is baked into the Vite bundle, so toggling a
flag is a one-line edit to that JSON followed by a frontend rebuild/redeploy. Evaluation goes
through OpenFeature's in-memory provider so call sites depend only on the neutral helper
(`isEnabled` / `isBillingEnabled` from `@/lib/feature-flags`).

A `billing` **master** flag gates all subscription UI
([FE-021](FE-021-subscription-access-control.md),
[FE-022](FE-022-subscription-checkout.md),
[FE-023](FE-023-subscription-management.md)) and the billing guidance in the user guide
([FE-016](FE-016-instructions-docs-page.md)). It ships **OFF**. When OFF:
- `SubscriptionGuard` is a pass-through — every page (premium included) renders with no paywall,
  and the `useSubscription` polling is skipped entirely (the gate never mounts the subscription
  logic).
- The owner-only "Manage Subscription" sidebar entry and its `ManageSubscriptionDialog` are
  hidden (the `useSubscription` "expiring soon" poll behind them does not run).
- The `/docs` user guide hides its Subscribing, Free Trial, and Managing Billing sections (and
  their TOC entries), the subscription FAQ, and inline billing mentions.

On top of the master flag, **per-feature paywall flags** implement the freemium model
([FE-021](FE-021-subscription-access-control.md)): a premium route's `SubscriptionGuard` gates
only when **both** `billing` and that route's flag are ON. There is **no real premium feature
yet** — `paywall_test_feature` is a placeholder (ships `enabled: true`) and no route is wrapped,
so it gates nothing.

This mirrors the backend flags ([BE-017](../backend/BE-017-feature-flags.md)); the two config
files are kept in sync manually. The backend is the real enforcement boundary, so even with the
UI flag mismatched the API gate ([BE-014](../backend/BE-014-subscription-access-control.md))
still governs access.

## Scope
- Module: `frontend/src/lib/feature-flags.ts` — imports the JSON config, registers an
  OpenFeature `InMemoryProvider`, and exposes `isEnabled(name)` and `isBillingEnabled()`. A
  test-only `setFlagsForTesting({...})` swaps the active flag map.
- Config: `frontend/src/config/feature-flags.json` —
  `{ "billing": { "enabled": false }, "paywall_test_feature": { "enabled": true } }`.
- Call sites:
  - `frontend/src/features/subscription/subscription-guard.tsx` — `SubscriptionGuard` takes a
    `featureFlag` prop and returns its children directly when billing is off **or** the named
    feature flag is off; otherwise renders the inner `SubscriptionGate` that runs
    `useSubscription` (keeps hooks unconditional). **No production route wraps it yet** — it is
    retained infrastructure for the first real premium feature.
  - `frontend/src/features/sidebar/app-sidebar.tsx` — the "Manage Subscription" item is split
    into `ManageSubscriptionItem` (which owns the `useSubscription` poll) and rendered, along
    with `ManageSubscriptionDialog`, only when billing is on.
  - `frontend/src/features/instructions/instructions-page.tsx` — filters the billing TOC
    entries and FAQ and conditionally renders the billing sections / inline mentions.
- Dependency: `@openfeature/web-sdk` (added to `frontend/package.json`).

## Edge Cases
- **Unknown flag name:** `isEnabled` returns the `false` default (feature off).
- **Flag spec without `enabled`:** treated as `false`.
- **Flag is a build-time constant:** it does not change during a session; the guard splits a
  child component out so React's rules-of-hooks are not violated by an early return.
- **UI/API flag mismatch:** harmless — the backend gate ([BE-014](../backend/BE-014-subscription-access-control.md))
  is the source of truth; the UI flag only controls what is shown.

## Acceptance Criteria
- [ ] With `billing` OFF (default), every page renders with no paywall and no subscription
      spinner (and no route is wrapped, so this holds with `billing` ON too).
- [ ] With `billing` OFF, the sidebar shows no "Manage Subscription" entry and the dialog is
      not mounted.
- [ ] With `billing` OFF, the `/docs` user guide hides the Subscribing, Free Trial, and
      Managing Billing sections while still rendering the rest of the guide.
- [ ] With `billing` OFF, no `getLeague`-driven subscription poll runs for the guard or sidebar.
- [ ] `paywall_test_feature` gates nothing today — it is a placeholder kept so the mechanism and
      pricing table stay wired for the first real premium feature.
- [ ] An unknown flag evaluates to `false`.

## Sources
`frontend/src/lib/feature-flags.ts`, `frontend/src/config/feature-flags.json`,
`frontend/src/features/subscription/subscription-guard.tsx`,
`frontend/src/features/sidebar/app-sidebar.tsx`,
[BE-017](../backend/BE-017-feature-flags.md) (backend mirror).
