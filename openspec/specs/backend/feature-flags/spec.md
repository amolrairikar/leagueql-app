# feature-flags Specification

## Purpose
Provide a vendor-neutral backend feature-flag layer using OpenFeature. Flag state lives in a single AWS SSM Parameter Store parameter (a standard-tier `String`, one per environment) holding the flag JSON, read at runtime via `ssm:GetParameter` through the Lambda's IAM role — so toggling a flag is an out-of-band edit to the parameter with no redeploy. Evaluation goes through OpenFeature's in-memory provider so call sites depend only on the neutral client. The frontend resolves the same flags via the public `GET /feature-flags` endpoint, so both tiers agree.

## Requirements

### Requirement: Fail safe when no flag source
When `FEATURE_FLAGS_SSM_PARAM` is unset or the parameter is missing/unreachable, every flag SHALL read as off, without raising an import error, and an unknown flag name SHALL resolve to `False`.

#### Scenario: No SSM parameter configured
- **WHEN** `FEATURE_FLAGS_SSM_PARAM` is unset (local/tests)
- **THEN** there is no flag source, the `ssm` client is never created, and every flag reads `False`

#### Scenario: Parameter missing or unreachable
- **WHEN** the parameter is missing (`ParameterNotFound`) or a refresh fails
- **THEN** flags fall back to the last-known values, or the all-off default on the initial load, rather than flipping to a surprise state

#### Scenario: Unknown flag
- **WHEN** `is_enabled` is called for an unknown flag name or a spec without `enabled`
- **THEN** it returns the `False` default

### Requirement: Toggle without redeploy
Editing the feature-flag parameter value SHALL change backend behavior within the TTL window (`FEATURE_FLAGS_TTL_SECONDS`, default 45s) with no redeploy.

#### Scenario: Console toggle
- **WHEN** the feature-flag parameter value is edited in the SSM console
- **THEN** backend behavior reflects the new value after the next TTL refresh, without a redeploy

### Requirement: Public feature-flags endpoint
`GET /feature-flags` SHALL be unauthenticated and return the resolved, whitelisted global flag map under the standard envelope with `Cache-Control: no-store`.

#### Scenario: SPA reads flags before sign-in
- **WHEN** the SPA calls `GET /feature-flags`
- **THEN** it returns `{ "detail": "Feature flags", "data": { <whitelisted flags> } }` unauthenticated, served `Cache-Control: no-store`

#### Scenario: Flag whitelist
- **WHEN** a new frontend-consumed flag is added
- **THEN** it is exposed only if explicitly added to `get_feature_flags` (the payload whitelists what it exposes)
