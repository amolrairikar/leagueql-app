# BE-017: Feature Flags (OpenFeature + SSM Parameter Store)

## Description
Provides a vendor-neutral feature-flag layer for the backend using
[OpenFeature](https://openfeature.dev/). Flag state is the source-of-truth in a single
**AWS SSM Parameter Store** parameter (a standard-tier `String`, one per environment) holding
the flag JSON, and is read at **runtime** through the boto3 `ssm` `GetParameter` API — so
toggling a flag is an edit to the parameter value in the SSM console, with **no code change and
no redeploy**. The parameter is read via the Lambda's **IAM role** (no API key). Evaluation goes
through OpenFeature's in-memory provider so call sites depend only on the neutral OpenFeature
client (`common.feature_flags.is_enabled` / `is_billing_enabled`), not on the flag source.

> Standard-tier SSM parameters are **free** for both storage and `GetParameter` calls, unlike
> AWS AppConfig (the previous source), which billed per "configuration received" on every
> Lambda cold start / session reset across both regions. The flag shape and behavior are
> unchanged; only the storage backend moved.

There is **no bundled JSON config**. The Lambdas select SSM only when `FEATURE_FLAGS_SSM_PARAM`
is set (the deployed functions). Otherwise — local dev and tests — there is no flag source and
**every flag defaults to `False`** (feature off). The same fail-safe applies if the parameter is
missing or unreachable.

A `billing` **master** flag gates all Stripe billing behavior
([BE-014](BE-014-subscription-access-control.md), [BE-015](BE-015-stripe-billing.md)). It defaults
**OFF**. When OFF:
- `require_active_subscription` is a no-op for every feature — every league reaches all
  endpoints (premium included) regardless of `subscription_end_time` (full access).
- `POST /leagues/{id}/checkout-session` and `POST /billing-portal-session` return `404`.
- The Stripe webhook Lambda returns `200` without processing (no subscription-state writes).

On top of the master flag, the **`premium_feature`** flag implements the freemium model
([BE-014](BE-014-subscription-access-control.md)): a premium feature is gated only when **both**
`billing` and `premium_feature` are ON. Every premium feature shares this one flag, so they are
all gated identically. The frontend gates the schedule-swap simulator
([FE-031](../frontend/FE-031-schedule-swap-simulator.md)) on it; **no backend endpoint enforces it
yet**. The helper `is_feature_paywalled(flag_name)` returns `is_billing_enabled() and is_enabled(flag_name)`,
and `require_active_subscription` short-circuits to a no-op when it is false. Gating a backend
endpoint is one call site with `PREMIUM_FEATURE`.

Beyond billing, the same mechanism carries **non-billing global flags** that gate frontend-only
UI. `banner` is one such flag: it gates the in-app informational banner
([FE-030](../frontend/FE-030-informational-banner.md)). The backend enforces nothing for it —
it is resolved like any other flag and surfaced to the SPA via `GET /feature-flags`.

The **`recap`** flag is a backend-only **kill-switch** for AI weekly matchup recap generation
([BE-022](BE-022-ai-weekly-matchup-recap.md)). Unlike every other flag it **defaults ON**:
recaps run unless the parameter explicitly carries `{"recap": {"enabled": false}}`. The helper
`is_recap_enabled()` returns `_client.get_boolean_value("recap", True)` — an unregistered flag
falls back to the `True` default (recaps on), and only a flag registered OFF returns `False`. The
recap **enqueue** (`record_pending_recap`) and the **generator** (`recap_generator`) each no-op
when it is off, so a single environment (e.g. DEV) can suppress the per-generation LLM spend by
adding the flag OFF **while `billing` stays on** (subscription features remain testable), with no
prod SSM change. It is not exposed via `GET /feature-flags` (backend enforcement only; the read
path already shows nothing when no recap exists).

The frontend resolves the same flags at runtime via the public `GET /feature-flags` endpoint
([FE-026](../frontend/FE-026-feature-flags.md)); both tiers read the same SSM source, so
they always agree.

## Public endpoint — `GET /feature-flags`
- **Unauthenticated** (no Clerk authorizer) so the SPA can load it before sign-in. Returns the
  resolved global flag map under the standard envelope:
  `{ "detail": "Feature flags", "data": { "billing": <bool>, "premium_feature": <bool>, "banner": <bool> } }`.
  The payload **whitelists** the flags it exposes, so a new frontend-consumed flag must be added
  to `get_feature_flags` explicitly.
- The payload is only non-sensitive global booleans (the same flags the frontend already shipped),
  so public exposure is fine. Served `Cache-Control: no-store` so a console toggle is picked up on
  the next load.

## Scope
- Module: `src/common/feature_flags.py` — selects the SSM source (when `FEATURE_FLAGS_SSM_PARAM`
  is set) via the `ssm` `GetParameter` API with a small in-process TTL cache (an initial fetch at
  cold start → re-fetch on a TTL, `FEATURE_FLAGS_TTL_SECONDS`, default 45s), registers an
  OpenFeature `InMemoryProvider`, and exposes `is_enabled(name)`, `is_billing_enabled()`, and
  `is_feature_paywalled(flag_name)` (= `is_billing_enabled() and is_enabled(flag_name)`), and
  `is_recap_enabled()` (= `get_boolean_value("recap", True)`, the default-on recap kill-switch),
  plus the `PREMIUM_FEATURE` (shared premium-feature), `BANNER` (FE-030), and `RECAP` (BE-022)
  flag-name constants. A test-only `_override_for_testing({...})` swaps the active flag map.
- Source of truth: an AWS SSM Parameter Store parameter (per environment, per region) named
  `/leagueql/<env>/feature-flags`, serving the same `{ "billing": { "enabled": false }, ... }` JSON
  shape the module parses. Like the Stripe/Axiom/Discord SSM values, it is **created and edited
  out-of-band** in the SSM console and is **never managed in Terraform** (no `aws_ssm_parameter`
  resource), so a toggle never needs a `terraform apply` / causes drift; only the `ssm:GetParameter`
  read grant lives in TF (`infrastructure/global/{dev,prod}`). The parameter is a plain `String`
  (the flags are non-secret global booleans already exposed via `GET /feature-flags`), not a
  `SecureString`. Until it is created the Lambdas read all flags off (fail-safe), so a fresh
  environment is safe before the value is set.
- Call sites:
  - `src/api/routes.py` — `get_feature_flags` (public `GET /feature-flags`),
    `create_checkout_session` and `create_billing_portal_session` raise `404` when billing is off.
  - `src/api/helpers.py` — `require_active_subscription(canonical_league_id, paywall_flag)`
    returns early when `is_feature_paywalled(paywall_flag)` is false (billing off or the
    feature's flag off). No production endpoint calls it yet.
  - `src/stripe_webhook/handler.py` — `lambda_handler` returns a `200` no-op when billing is off.
  - `src/common/recap_queue.py` — `record_pending_recap` no-ops when `is_recap_enabled()` is off
    (in addition to the billing/region no-ops).
  - `src/recap_generator/handler.py` — `_handle` returns `{"status": "skipped",
    "reason": "recap_disabled"}` when `is_recap_enabled()` is off, before any LLM spend.
- Dependency: `openfeature-sdk` + `boto3` (boto3/botocore already present). `FEATURE_FLAGS_SSM_PARAM`
  is set on the API and stripe_webhook Lambdas (`infrastructure/regional/main.tf`); the execution
  roles grant `ssm:GetParameter` on the feature-flag parameter in both regions
  (`infrastructure/global/{dev,prod}/main.tf`).
- Tests: the Stripe **integration** suite (`tests/integration/stripe/`) runs against the deployed
  billing endpoints, which only behave as tested when billing is ON. Its `environment.py` queries
  the deployed public `GET /feature-flags` (the real resolved flag state) and **skips every
  scenario** when billing is off (and the CI job gates its run step on the same endpoint). The
  ESPN/Sleeper integration suites are unaffected. Unit/component suites default the flag via the
  `_override_for_testing` seam (no SSM env, no network) and add explicit OFF-path cases.

## Edge Cases
- **`FEATURE_FLAGS_SSM_PARAM` unset (local / tests):** there is no flag source, so every flag
  (including `billing`) reads `False`, and the `ssm` client is never created (no network).
- **Parameter unreachable / fetch error:** a failed refresh keeps the last-known flags (or the
  empty all-off default on the initial fetch) — flags never flip to a surprise state because SSM
  hiccuped.
- **Parameter missing / never populated:** `GetParameter` raises `ParameterNotFound`, treated as a
  fetch error → all off on the initial load.
- **Unknown flag name / spec without `enabled`:** `is_enabled` returns the `False` default.
- **`recap` flag absent (default / local / tests):** `is_recap_enabled()` falls back to its `True`
  default, so recaps stay on; only an explicit `{"recap": {"enabled": false}}` disables them.
- **Toggle latency:** a console edit takes effect after the next TTL refresh
  (≤ `FEATURE_FLAGS_TTL_SECONDS`) — seconds, not instant.

## Acceptance Criteria
- [ ] With `billing` OFF (default), all endpoints succeed regardless of `subscription_end_time`
      (no endpoint is subscription-gated; [BE-014](BE-014-subscription-access-control.md)).
- [ ] With `billing` OFF, `POST /leagues/{id}/checkout-session` and `POST /billing-portal-session`
      return `404`.
- [ ] With `billing` OFF, the Stripe webhook returns `200` and writes no subscription state.
- [ ] `is_feature_paywalled` is true only when both the master `billing` flag and the named
      per-feature flag are ON.
- [ ] `premium_feature` is the shared flag every premium feature gates on; the frontend gates the
      schedule-swap simulator (FE-031) on it, and no backend endpoint enforces it yet.
- [ ] With `FEATURE_FLAGS_SSM_PARAM` unset, or the parameter unreachable/missing, all flags read as
      off (fail-safe), not an import error.
- [ ] Editing the feature-flag parameter value in the SSM console changes backend behavior within
      the TTL window **without a redeploy**.
- [ ] `GET /feature-flags` is unauthenticated and returns the resolved global flag map.
- [ ] `is_recap_enabled()` defaults **on** (`True`) when the `recap` flag is absent, and only an
      explicit `{"recap": {"enabled": false}}` returns `False`.
- [ ] With `recap` OFF, both `record_pending_recap` and the recap generator no-op (no LLM spend)
      even while `billing` is ON.

## Sources
`src/common/feature_flags.py`, `src/api/routes.py` (`get_feature_flags`, billing endpoints),
`src/api/helpers.py`, `src/stripe_webhook/handler.py`, `src/common/recap_queue.py`,
`src/recap_generator/handler.py` (`recap` kill-switch, BE-022),
`infrastructure/regional/main.tf`, `infrastructure/global/{dev,prod}/main.tf`
(`ssm:GetParameter` grants; the parameter itself is set out-of-band), `docs/api/openapi_spec.yaml`
(`/feature-flags`),
[FE-026](../frontend/FE-026-feature-flags.md) (frontend consumer).
