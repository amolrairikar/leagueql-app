# BE-017: Feature Flags (OpenFeature + SSM Parameter Store)

## Description
Provides a vendor-neutral feature-flag layer for the backend using
[OpenFeature](https://openfeature.dev/). Flag state is the source-of-truth in a single
**AWS SSM Parameter Store** parameter (a standard-tier `String`, one per environment) holding
the flag JSON, and is read at **runtime** through the boto3 `ssm` `GetParameter` API — so
toggling a flag is an edit to the parameter value in the SSM console, with **no code change and
no redeploy**. The parameter is read via the Lambda's **IAM role** (no API key). Evaluation goes
through OpenFeature's in-memory provider so call sites depend only on the neutral OpenFeature
client (`common.feature_flags.is_enabled`), not on the flag source.

> Standard-tier SSM parameters are **free** for both storage and `GetParameter` calls, unlike
> AWS AppConfig (the previous source), which billed per "configuration received" on every
> Lambda cold start / session reset across both regions. The flag shape and behavior are
> unchanged; only the storage backend moved.

There is **no bundled JSON config**. The Lambdas select SSM only when `FEATURE_FLAGS_SSM_PARAM`
is set (the deployed functions). Otherwise — local dev and tests — there is no flag source and
**every flag defaults to `False`** (feature off). The same fail-safe applies if the parameter is
missing or unreachable.

The mechanism carries **global flags** that gate frontend-only UI. `banner` is one such flag:
it gates the in-app informational banner
([FE-030](../frontend/FE-030-informational-banner.md)). The backend enforces nothing for it —
it is resolved like any other flag and surfaced to the SPA via `GET /feature-flags`.

The frontend resolves the same flags at runtime via the public `GET /feature-flags` endpoint
([FE-026](../frontend/FE-026-feature-flags.md)); both tiers read the same SSM source, so
they always agree.

## Public endpoint — `GET /feature-flags`
- **Unauthenticated** (no Clerk authorizer) so the SPA can load it before sign-in. Returns the
  resolved global flag map under the standard envelope:
  `{ "detail": "Feature flags", "data": { "banner": <bool> } }`.
  The payload **whitelists** the flags it exposes, so a new frontend-consumed flag must be added
  to `get_feature_flags` explicitly.
- The payload is only non-sensitive global booleans (the same flags the frontend already shipped),
  so public exposure is fine. Served `Cache-Control: no-store` so a console toggle is picked up on
  the next load.

## Scope
- Module: `src/common/feature_flags.py` — selects the SSM source (when `FEATURE_FLAGS_SSM_PARAM`
  is set) via the `ssm` `GetParameter` API with a small in-process TTL cache (an initial fetch at
  cold start → re-fetch on a TTL, `FEATURE_FLAGS_TTL_SECONDS`, default 45s), registers an
  OpenFeature `InMemoryProvider`, and exposes `is_enabled(name)` plus the `BANNER` (FE-030)
  flag-name constant. A test-only `_override_for_testing({...})` swaps the active flag map.
- Source of truth: an AWS SSM Parameter Store parameter (per environment, per region) named
  `/leagueql/<env>/feature-flags`, serving the same `{ "banner": { "enabled": false }, ... }` JSON
  shape the module parses. Like the Axiom/Discord SSM values, it is **created and edited
  out-of-band** in the SSM console and is **never managed in Terraform** (no `aws_ssm_parameter`
  resource), so a toggle never needs a `terraform apply` / causes drift; only the `ssm:GetParameter`
  read grant lives in TF (`infrastructure/global/{dev,prod}`). The parameter is a plain `String`
  (the flags are non-secret global booleans already exposed via `GET /feature-flags`), not a
  `SecureString`. Until it is created the Lambdas read all flags off (fail-safe), so a fresh
  environment is safe before the value is set.
- Call sites:
  - `src/api/routes.py` — `get_feature_flags` (public `GET /feature-flags`).
- Dependency: `openfeature-sdk` + `boto3` (boto3/botocore already present). `FEATURE_FLAGS_SSM_PARAM`
  is set on the API Lambda (`infrastructure/regional/main.tf`); the execution role grants
  `ssm:GetParameter` on the feature-flag parameter in both regions
  (`infrastructure/global/{dev,prod}/main.tf`).
- Tests: unit/component suites default the flags via the `_override_for_testing` seam (no SSM env,
  no network).

## Edge Cases
- **`FEATURE_FLAGS_SSM_PARAM` unset (local / tests):** there is no flag source, so every flag
  reads `False`, and the `ssm` client is never created (no network).
- **Parameter unreachable / fetch error:** a failed refresh keeps the last-known flags (or the
  empty all-off default on the initial fetch) — flags never flip to a surprise state because SSM
  hiccuped.
- **Parameter missing / never populated:** `GetParameter` raises `ParameterNotFound`, treated as a
  fetch error → all off on the initial load.
- **Unknown flag name / spec without `enabled`:** `is_enabled` returns the `False` default.
- **Toggle latency:** a console edit takes effect after the next TTL refresh
  (≤ `FEATURE_FLAGS_TTL_SECONDS`) — seconds, not instant.

## Acceptance Criteria
- [ ] With `FEATURE_FLAGS_SSM_PARAM` unset, or the parameter unreachable/missing, all flags read as
      off (fail-safe), not an import error.
- [ ] Editing the feature-flag parameter value in the SSM console changes backend behavior within
      the TTL window **without a redeploy**.
- [ ] `GET /feature-flags` is unauthenticated and returns the resolved global flag map.
- [ ] An unknown flag name resolves to `False`.

## Sources
`src/common/feature_flags.py`, `src/api/routes.py` (`get_feature_flags`),
`infrastructure/regional/main.tf`, `infrastructure/global/{dev,prod}/main.tf`
(`ssm:GetParameter` grants; the parameter itself is set out-of-band), `docs/api/openapi_spec.yaml`
(`/feature-flags`),
[FE-026](../frontend/FE-026-feature-flags.md) (frontend consumer).
