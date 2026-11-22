# Design

## Context

The shared `infrastructure/modules/api-gw` module configures the `$default` stage's `access_log_settings` with a JSON format (IP, user agent, route, path, status, latency) written to `/aws/apigateway/leagueql-api-<env>-east`. The API is an HTTP API (`aws_apigatewayv2`) fronted by a Clerk JWT authorizer, whose verified claims are exposed to the access-log format as `$context.authorizer.claims.<claim>`. The Lambda already reads the same `sub` via `get_authenticated_user`, but never logs it. Log retention for the group is 7 days (`infrastructure/regional/main.tf`). See proposal.md for motivation.

## Goals / Non-Goals

**Goals:**
- Attribute every authenticated request in the access log to a Clerk user ID with a one-field format change.

**Non-Goals:**
- Logging the user ID in Lambda application logs or OTel span attributes (a separate, optional change; the gateway log is the source for non-member `403`s that never reach application logging).
- Changing retention, adding log metric filters, alarms, or dashboards.
- Logging any other claim (email, name) or the JWT itself.

## Decisions

- **Log `$context.authorizer.claims.sub` as `userId`.** It is the exact identifier stored in DynamoDB (`owner_user_id`, `members`), so a log line can be compared directly to a league's METADATA. Alternatives: `$context.authorizer.principalId` (not populated for HTTP API JWT authorizers); logging the full `claims` object (leaks email and other PII and bloats entries) — rejected.
- **Gateway layer rather than application code.** It covers every route, including requests rejected by the Lambda with `403`/`404` and any that fail before the handler logs anything, with zero application changes or deploy of the Lambda.
- **Add a new key, keep existing ones.** Existing queries and the `api_gw_5xx` alarm (stage metrics, not log-derived) are unaffected.
- **Public routes log empty.** HTTP API substitutes an empty/`-` value when a context variable is absent; no conditional logic is needed.

## Risks / Trade-offs

- [Clerk user ID is a persistent pseudonymous identifier, now in logs] → Access log retention is only 7 days, and the ID is already stored in DynamoDB; do not add email/name. Update the privacy page only if it enumerates logged data (check during implementation).
- [Variable resolves empty because the claim is surfaced differently than expected] → Verify after deploy on dev by reading a recent authenticated request's entry; if empty, adjust the variable before prod.
- [Format change applies via `auto_deploy`/stage update with `create_before_destroy`] → Low risk; confirm in `terraform plan` that only the stage's `access_log_settings.format` changes.
- [7-day retention limits retroactive proof] → Entries for the already-reported failure (Nov 18) will not contain `userId` and will age out; evidence applies only to future attempts, which is acceptable.

## Migration Plan

1. `terraform plan`/apply to dev, make an authenticated request, confirm `userId` in the log entry.
2. Apply to prod; confirm the same for a prod request and that a public route (`/health`) logs an empty `userId`.
3. Rollback: revert the one-line change and re-apply; no data migration involved.
