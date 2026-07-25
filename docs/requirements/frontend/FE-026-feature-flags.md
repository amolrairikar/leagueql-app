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
depend only on the neutral helper (`isEnabled` from `@/lib/feature-flags`).

The mechanism carries **global flags** that gate frontend-only UI. `banner` is one such flag:
it gates the in-app informational banner ([FE-030](FE-030-informational-banner.md)), read via
the `isBannerEnabled()` helper.

## Resolution & reactivity
- `initFeatureFlags()` runs once at bootstrap (`app/main.tsx`, before first paint), fetching
  `${API_BASE_URL}/feature-flags` (bare `fetch`, no auth) and building the `InMemoryProvider` from
  the response. It is a **no-op under Vitest** so component tests never hit the network.
- A light refresh (a poll interval + a refresh on `visibilitychange`) re-fetches the flags so a
  console toggle is picked up without a reload. The refresh is **idempotent**: it swaps the
  provider (emitting `PROVIDER_READY` / `PROVIDER_CONFIGURATION_CHANGED`) **only when the resolved
  flag values actually changed** — compared key-sorted against the currently applied map. A refresh
  that returns the same values (the common case, e.g. every tab-focus refresh) is a no-op, so it
  does **not** emit an event and does **not** remount the app.
- `FeatureFlagProvider` (`app/feature-flags-provider.tsx`, wrapping `<App />`) listens for those
  events and **remounts the subtree** (via a changing `key`) so the synchronous `isEnabled()` call
  sites — which take no flag props — re-evaluate. The initial (already-applied) flags are skipped,
  so the app remounts only on a genuine later change (a rare operator action).
- **Fail-safe:** a non-200, network error, or unreachable backend leaves the current (or initial
  all-off) provider in place — a transient outage never flips a flag on.

## Scope
- Module: `frontend/src/lib/feature-flags.ts` — registers an all-off `InMemoryProvider` at load,
  exposes `isEnabled(name)` / `isBannerEnabled()`, `initFeatureFlags()` (fetch + refresh), and
  `refreshFlags()` (the mapping seam). A test-only `setFlagsForTesting({...})` swaps the active
  flag map.
- Source: the public `GET /feature-flags` endpoint (BE-017), resolved from AWS SSM Parameter Store.
  No checked-in JSON.
- Call sites:
  - `frontend/src/components/banner.tsx` — the informational banner renders only when
    `isBannerEnabled()` is true.
- Dependency: `@openfeature/web-sdk` (`frontend/package.json`). No new packages, no CSP change —
  `api.leagueql.com` (and the dev API origin) are already allowed by `connect-src`
  ([FE-024](FE-024-security-headers.md)).

## Edge Cases
- **Flags not yet resolved / backend unreachable:** every flag reads `false` (feature off).
- **Unknown flag name / spec without `enabled`:** `isEnabled` returns the `false` default.
- **Runtime toggle mid-session:** the refresh swaps the provider and the app remounts so the UI
  reflects the new flags; this is a soft re-render of the tree (current route preserved).
- **Refresh with no change (incl. every tab-focus refresh):** the resolved flags match the applied
  map, so the provider is not swapped and the app does not remount — switching tabs does not reset
  component state.

## Acceptance Criteria
- [ ] With flags unresolved / the backend unreachable, every flag reads `false` (fail-safe).
- [ ] An unknown flag evaluates to `false`.
- [ ] Editing the feature-flag parameter value in the SSM console changes the UI within the refresh
      window **without a rebuild**.
- [ ] A refresh that resolves the same flag values (e.g. returning to the tab) does not swap the
      provider or remount the app.
- [ ] `initFeatureFlags()` is a no-op under Vitest (no `/feature-flags` fetch in component tests).

## Sources
`frontend/src/lib/feature-flags.ts`, `frontend/src/app/feature-flags-provider.tsx`,
`frontend/src/app/main.tsx`,
[BE-017](../backend/BE-017-feature-flags.md) (backend source + `GET /feature-flags`).
