# BE-017: Feature Flags (OpenFeature + AWS AppConfig)

## Description
Provides a vendor-neutral feature-flag layer for the backend using
[OpenFeature](https://openfeature.dev/). Flag state is the source-of-truth in **AWS AppConfig**
(a feature-flag configuration profile, one per environment) and is read at **runtime** through
the boto3 `appconfigdata` Data API — so toggling a flag is a change in the AppConfig console + an
AppConfig deployment, with **no code change and no redeploy**. AppConfig is read via the Lambda's
**IAM role** (no SSM secret, no API key). Evaluation goes through OpenFeature's in-memory provider
so call sites depend only on the neutral OpenFeature client
(`common.feature_flags.is_enabled` / `is_billing_enabled`), not on the flag source.

There is **no bundled JSON config**. The Lambdas select AppConfig only when
`APPCONFIG_APPLICATION` / `APPCONFIG_ENVIRONMENT` / `APPCONFIG_PROFILE` are all set (the deployed
functions). Otherwise — local dev and tests — there is no flag source and **every flag defaults
to `False`** (feature off). The same fail-safe applies if AppConfig is unreachable.

A `billing` **master** flag gates all Stripe billing behavior
([BE-014](BE-014-subscription-access-control.md), [BE-015](BE-015-stripe-billing.md)). It defaults
**OFF**. When OFF:
- `require_active_subscription` is a no-op for every feature — every league reaches all
  endpoints (premium included) regardless of `subscription_end_time` (full access).
- `POST /leagues/{id}/checkout-session` and `POST /billing-portal-session` return `404`.
- The Stripe webhook Lambda returns `200` without processing (no subscription-state writes).

On top of the master flag, **per-feature paywall flags** implement the freemium model
([BE-014](BE-014-subscription-access-control.md)): a premium feature is gated only when **both**
`billing` and that feature's flag are ON. There is **no real premium feature yet** —
`paywall_test_feature` is a placeholder that gates nothing (no endpoint calls the gate with it).
The helper `is_feature_paywalled(flag_name)` returns `is_billing_enabled() and is_enabled(flag_name)`,
and `require_active_subscription` short-circuits to a no-op when it is false. Adding the first real
premium feature is a new `paywall_*` flag plus one call site.

The frontend resolves the same flags at runtime via the public `GET /feature-flags` endpoint
([FE-026](../frontend/FE-026-feature-flags.md)); both tiers read the same AppConfig source, so
they always agree.

## Public endpoint — `GET /feature-flags`
- **Unauthenticated** (no Clerk authorizer) so the SPA can load it before sign-in. Returns the
  resolved global flag map under the standard envelope:
  `{ "detail": "Feature flags", "data": { "billing": <bool>, "paywall_test_feature": <bool> } }`.
- The payload is only non-sensitive global booleans (the same flags the frontend already shipped),
  so public exposure is fine. Served `Cache-Control: no-store` so a console toggle is picked up on
  the next load.

## Scope
- Module: `src/common/feature_flags.py` — selects the AppConfig source (when the three
  `APPCONFIG_*` env vars are set) via the `appconfigdata` Data API with a small in-process TTL
  cache (`start_configuration_session` at cold start → `get_latest_configuration` on a TTL,
  `APPCONFIG_TTL_SECONDS`, default 45s), registers an OpenFeature `InMemoryProvider`, and exposes
  `is_enabled(name)`, `is_billing_enabled()`, and `is_feature_paywalled(flag_name)` (=
  `is_billing_enabled() and is_enabled(flag_name)`), plus the `PAYWALL_TEST_FEATURE` placeholder
  flag-name constant. A test-only `_override_for_testing({...})` swaps the active flag map.
- Source of truth: AWS AppConfig feature-flag profile (per environment), serving the same
  `{ "billing": { "enabled": false }, ... }` shape the module parses. Flag values + deployments are
  set in the AppConfig console (the runtime toggle); the AppConfig application / environment /
  profile / rollout strategy are scaffolded in Terraform (`infrastructure/modules/appconfig`,
  instantiated per region in `infrastructure/global/{dev,prod}`), but the values are **not** managed
  in TF (so a toggle never needs a `terraform apply`).
- Call sites:
  - `src/api/routes.py` — `get_feature_flags` (public `GET /feature-flags`),
    `create_checkout_session` and `create_billing_portal_session` raise `404` when billing is off.
  - `src/api/helpers.py` — `require_active_subscription(canonical_league_id, paywall_flag)`
    returns early when `is_feature_paywalled(paywall_flag)` is false (billing off or the
    feature's flag off). No production endpoint calls it yet.
  - `src/stripe_webhook/handler.py` — `lambda_handler` returns a `200` no-op when billing is off.
- Dependency: `openfeature-sdk` + `boto3` (boto3/botocore already present). The three `APPCONFIG_*`
  env vars are set on the API and stripe_webhook Lambdas (`infrastructure/regional/main.tf`); the
  execution roles grant `appconfig:StartConfigurationSession` + `appconfig:GetLatestConfiguration`
  on the feature-flag configuration in both regions (`infrastructure/global/{dev,prod}/main.tf`).
- Tests: the Stripe **integration** suite (`tests/integration/stripe/`) runs against the deployed
  billing endpoints, which only behave as tested when billing is ON. Its `environment.py` queries
  the deployed public `GET /feature-flags` (the real resolved AppConfig state) and **skips every
  scenario** when billing is off (and the CI job gates its run step on the same endpoint). The
  ESPN/Sleeper integration suites are unaffected. Unit/component suites default the flag via the
  `_override_for_testing` seam (no AppConfig env, no network) and add explicit OFF-path cases.

## Edge Cases
- **AppConfig env vars unset (local / tests):** there is no flag source, so every flag (including
  `billing`) reads `False`, and the `appconfigdata` client is never created (no network).
- **AppConfig unreachable / fetch error:** a failed refresh keeps the last-known flags (or the
  empty all-off default on the initial fetch) and drops the session token so the next poll
  re-establishes it — flags never flip to a surprise state because AppConfig hiccuped.
- **No deployment yet in AppConfig:** `get_latest_configuration` returns an empty body, treated as
  "no flags" → all off.
- **Unknown flag name / spec without `enabled`:** `is_enabled` returns the `False` default.
- **Toggle latency:** a console toggle takes effect after the AppConfig deployment completes + the
  next TTL refresh (≤ `APPCONFIG_TTL_SECONDS`) — seconds-to-minutes, not instant.

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
- [ ] With the `APPCONFIG_*` env vars unset, or AppConfig unreachable, all flags read as off
      (fail-safe), not an import error.
- [ ] Flipping a flag in the AppConfig console (and deploying it) changes backend behavior within
      the TTL window **without a redeploy**.
- [ ] `GET /feature-flags` is unauthenticated and returns the resolved global flag map.

## Sources
`src/common/feature_flags.py`, `src/api/routes.py` (`get_feature_flags`, billing endpoints),
`src/api/helpers.py`, `src/stripe_webhook/handler.py`,
`infrastructure/modules/appconfig`, `infrastructure/regional/main.tf`,
`infrastructure/global/{dev,prod}/main.tf`, `docs/api/openapi_spec.yaml` (`/feature-flags`),
[FE-026](../frontend/FE-026-feature-flags.md) (frontend consumer).
