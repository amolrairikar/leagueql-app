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

A `billing` **master** flag gates all Stripe billing behavior
([BE-014](BE-014-subscription-access-control.md), [BE-015](BE-015-stripe-billing.md)). It ships
**OFF**. When OFF:
- `require_active_subscription` is a no-op for every feature — every league reaches all
  endpoints (premium included) regardless of `subscription_end_time` (full access).
- `POST /leagues/{id}/checkout-session` and `POST /billing-portal-session` return `404`.
- The Stripe webhook Lambda returns `200` without processing (no subscription-state writes).

On top of the master flag, **per-feature paywall flags** implement the freemium model
([BE-014](BE-014-subscription-access-control.md)): a premium feature is gated only when **both**
`billing` and that feature's flag are ON. There is **no real premium feature yet** —
`paywall_test_feature` is a placeholder that ships `enabled: true` but gates nothing (no endpoint
calls the gate with it). The helper `is_feature_paywalled(flag_name)` returns
`is_billing_enabled() and is_enabled(flag_name)`, and `require_active_subscription` short-circuits
to a no-op when it is false. Adding the first real premium feature is a new `paywall_*` flag plus
one call site.

Flipping `billing` to `enabled: true` (and redeploying) restores the BE-014/BE-015 behavior,
with the subscription gate then applying **only** to premium features whose `paywall_*` flag is
ON. The frontend has its own mirror config
([FE-026](../frontend/FE-026-feature-flags.md)); the two files are kept in sync manually.

## Scope
- Module: `src/common/feature_flags.py` — loads `feature_flags.json` (relative to the module),
  registers an OpenFeature `InMemoryProvider`, and exposes `is_enabled(name)`,
  `is_billing_enabled()`, and `is_feature_paywalled(flag_name)` (= `is_billing_enabled() and
  is_enabled(flag_name)`), plus the `PAYWALL_TEST_FEATURE` placeholder flag-name constant. A
  test-only `_override_for_testing({...})` swaps the active flag map.
- Config: `src/common/feature_flags.json` —
  `{ "billing": { "enabled": false }, "paywall_test_feature": { "enabled": true } }`.
- Call sites:
  - `src/api/helpers.py` — `require_active_subscription(canonical_league_id, paywall_flag)`
    returns early when `is_feature_paywalled(paywall_flag)` is false (billing off or the
    feature's flag off). No production endpoint calls it yet.
  - `src/api/routes.py` — `create_checkout_session`, `create_billing_portal_session` raise `404`
    when billing is off.
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
- [ ] With `billing` OFF (default), all endpoints succeed regardless of `subscription_end_time`
      (no endpoint is subscription-gated; [BE-014](BE-014-subscription-access-control.md)).
- [ ] With `billing` OFF, `POST /leagues/{id}/checkout-session` and `POST /billing-portal-session`
      return `404`.
- [ ] With `billing` OFF, the Stripe webhook returns `200` and writes no subscription state.
- [ ] `is_feature_paywalled` is true only when both the master `billing` flag and the named
      per-feature flag are ON.
- [ ] `paywall_test_feature` gates nothing today — it is a placeholder kept so the mechanism and
      pricing table stay wired for the first real premium feature.
- [ ] A missing or malformed `feature_flags.json` causes all flags to read as off (fail-safe),
      not an import error.

## Sources
`src/common/feature_flags.py`, `src/common/feature_flags.json`,
`scripts/deployment_scripts/build_lambda_zip.sh` (bundling), `src/api/helpers.py`,
`src/api/routes.py`, `src/stripe_webhook/handler.py`,
[FE-026](../frontend/FE-026-feature-flags.md) (frontend mirror).
