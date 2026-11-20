# Proposal

## Why

No log records *which authenticated user* made an API request. The Lambda logs carry only `correlation_id`/`trace_id`, and the API Gateway access log (`infrastructure/modules/api-gw/main.tf`) records IP, user agent, route, and status but not the caller. When a Yahoo league (33519) failed to connect for a user hitting a non-member `403` loop, the leading theory — the user signed in with a different Clerk account than the league owner — could not be proven from logs. Adding the verified Clerk `sub` to the access log makes this class of support/debugging question answerable without extra instrumentation.

## What Changes

- Add `$context.authorizer.claims.sub` (the Clerk user ID the JWT authorizer already verified) as a `userId` field in the API Gateway `access_log_settings` JSON format, so every request line in `/aws/apigateway/leagueql-api-<env>-east` identifies the caller.
- Public (unauthenticated) routes, which never run the authorizer, log the field as empty/`-`; no behavior change for them.
- No application code, API contract, or response behavior changes. Infrastructure only.

## Capabilities

### New Capabilities
- `backend/api-access-logging`: the API Gateway access log records a structured line per request, including the authenticated caller's Clerk user ID.

### Modified Capabilities
<!-- None: no existing capability's requirements change. -->

## Impact

- `infrastructure/modules/api-gw/main.tf` — one added field in `access_log_settings.format`; applies to dev and prod stages via the shared module.
- CloudWatch log group `/aws/apigateway/leagueql-api-<env>-east` — new `userId` JSON key on each entry; existing keys unchanged, so current queries keep working.
- Privacy: the Clerk user ID is a pseudonymous identifier, already stored in DynamoDB (`owner_user_id`, `members`). Log retention of the group governs how long it persists (see design).
- No frontend, backend code, OpenAPI, DynamoDB, or architecture-diagram changes.
