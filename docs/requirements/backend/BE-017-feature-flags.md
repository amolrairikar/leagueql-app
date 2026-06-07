# BE-017: Feature Flags (OpenFeature)

## Description
Provides a vendor-neutral feature-flag layer for the backend using
[OpenFeature](https://openfeature.dev/). Flag state is read from a checked-in JSON config file,
`src/common/feature_flags.json`, that maps each flag name to `{ "enabled": <bool> }`. The file
is vendored into every Lambda deployment zip (the shared `src/common/` package is copied into
each function by `scripts/deployment_scripts/build_lambda_zip.sh`), so toggling a flag is a
one-line edit to that JSON followed by a redeploy — no code change. Evaluation goes through
OpenFeature's in-memory provider so call sites depend only on the neutral OpenFeature client
(`common.feature_flags.is_enabled` / `is_billing_enabled`), not on the config format or any
flag vendor.

A single `billing` flag currently exists and **gates all Stripe billing behavior**
([BE-014](BE-014-subscription-access-control.md), [BE-015](BE-015-stripe-billing.md)). It ships
**OFF**. When OFF:
- `require_active_subscription` is a no-op — every league reaches the gated data/write
  endpoints regardless of `subscription_end_time` (full access).
- `POST /leagues/{id}/checkout-session` and `POST /billing-portal-session` return `404`.
- The Stripe webhook Lambda returns `200` without processing (no subscription-state writes).

Flipping `billing` back to `enabled: true` (and redeploying) restores the BE-014/BE-015
behavior with no other change. The frontend has its own mirror config
([FE-026](../frontend/FE-026-feature-flags.md)); the two files are kept in sync manually.

## Scope
- Module: `src/common/feature_flags.py` — loads `feature_flags.json` (relative to the module),
  registers an OpenFeature `InMemoryProvider`, and exposes `is_enabled(name)` and
  `is_billing_enabled()`. A test-only `_override_for_testing({...})` swaps the active flag map.
- Config: `src/common/feature_flags.json` — `{ "billing": { "enabled": false } }`.
- Call sites (all guard on `is_billing_enabled()`):
  - `src/api/helpers.py` — `require_active_subscription` returns early when billing is off.
  - `src/api/routes.py` — `create_checkout_session`, `create_billing_portal_session` raise
    `404` when billing is off.
  - `src/stripe_webhook/handler.py` — `lambda_handler` returns a `200` no-op when billing is off.
- Dependency: `openfeature-sdk` (added to `src/api/requirements.txt`,
  `src/stripe_webhook/requirements.txt`, and the root `Pipfile`).
- Tests: the Stripe **integration** suite (`tests/integration/stripe/`) runs against the
  deployed billing endpoints, which only behave as tested when billing is ON. Its
  `environment.py` reads `is_billing_enabled()` and **skips every scenario** when the flag is
  off (and the CI job's run step is gated on the same flag via `feature_flags.json`). The
  ESPN/Sleeper integration suites are unaffected — they invoke the auto-refresh / onboarder
  Lambdas directly and never hit the subscription-gated API routes. Unit/component suites
  default the flag ON via test seams and add explicit OFF-path cases.

## Edge Cases
- **Missing / malformed config file:** loading fails safe to an empty config, so every flag
  (including `billing`) reads as `False` (feature off).
- **Unknown flag name:** `is_enabled` returns the `False` default.
- **Flag spec without `enabled`:** treated as `False`.
- **Config not bundled into a zip:** the build script copies all of `src/common/`, so the JSON
  is present wherever the module is; absent it, evaluation still fails safe to off.
- **Toggling at runtime:** not supported — flags are read from the bundled file at import time;
  a change requires a redeploy.

## Acceptance Criteria
- [ ] With `billing` OFF (default), gated endpoints (`GET /leagues/{id}/query`,
      `POST /leagues/{id}/migrate`, `POST /leagues/{id}/espn_members`, REFRESH) succeed
      regardless of `subscription_end_time`.
- [ ] With `billing` OFF, `POST /leagues/{id}/checkout-session` and `POST /billing-portal-session`
      return `404`.
- [ ] With `billing` OFF, the Stripe webhook returns `200` and writes no subscription state.
- [ ] With `billing` ON, BE-014/BE-015 behavior is unchanged (paywall `402`, working
      checkout/portal, webhook processing).
- [ ] A missing or malformed `feature_flags.json` causes all flags to read as off (fail-safe),
      not an import error.

## Sources
`src/common/feature_flags.py`, `src/common/feature_flags.json`,
`scripts/deployment_scripts/build_lambda_zip.sh` (bundling), `src/api/helpers.py`,
`src/api/routes.py`, `src/stripe_webhook/handler.py`,
[FE-026](../frontend/FE-026-feature-flags.md) (frontend mirror).
