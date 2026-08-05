# BE-023: API Health Check & Uptime Alerting

## Description
Exposes a **public liveness endpoint** for the API so an **external uptime monitor** can detect
and alert on outages, without waiting for real user traffic to surface an error.

**Public health endpoint — `GET /health`.** An **unauthenticated** liveness endpoint (no Clerk
authorizer, mirroring [BE-017](BE-017-feature-flags.md)'s `GET /feature-flags`) that returns
`200 { "detail": "Healthy!" }` whenever the FastAPI app is running. It is **liveness-only** — it
does not touch DynamoDB, S3, or any downstream dependency, so it reflects only whether the API
itself is up and reachable. This replaces the former authed root `GET /` health check (the JWT
authorizer made it un-probeable by an external monitor, which would get `401`, not `200`). The
root path `/` no longer exists.

**Uptime probing & alerting is handled by an external monitoring service — Better Stack** (the same
vendor used for tracing, [BE-020](BE-020-backend-otel-tracing.md) / [FE-029](../frontend/FE-029-frontend-observability.md)).
Two console-configured HTTP monitors probe the site and the API on a 1–5 min interval:
`https://leagueql.com` (the frontend) and `https://api.leagueql.com/health` (the API liveness
endpoint, optionally keyword-matching `Healthy!` on the body). Better Stack's own incident alerting
posts to the same Discord ops channel via its incoming-webhook integration — there is no AWS-side
probe or alarm, and **no application code or Terraform is involved** (monitors live entirely in the
Better Stack console).

> **History:** BE-023 originally shipped an AWS **Route 53 health check** on
> `https://api.leagueql.com/health` plus a CloudWatch `HealthCheckStatus` alarm that fanned out
> through the `lambda_alerts` SNS topic → `discord_notifier` Lambda. That was **removed** because
> Route 53's ~15 geographically-distributed health checkers probed the endpoint every 30s, each
> hit waking the 2 GB API Lambda through API Gateway (~1.3M invocations/month) — the request-driven
> cost dwarfed the flat health-check charge. An external monitor probing at a 1–5 min interval from
> a single location achieves the same liveness alerting at a fraction of the request volume (and
> typically $0 on a free tier). The `/health` endpoint itself is unchanged and is what the external
> monitor probes.

## Scope
- Endpoint: `src/api/routes.py` — `health()` handler at `GET /health` (returns `APIResponse(detail="Healthy!")`).
- API contract: `docs/api/openapi_spec.yaml` — the `/health` path with **no** `security` block
  and the standard `aws_proxy` integration to the API Lambda. The old `/` path is removed.
- **No AWS infrastructure** — the Route 53 health check and CloudWatch alarm have been removed from
  `infrastructure/regional/main.tf`. Uptime probing and alerting are delegated to an external
  monitoring service configured outside this repo.

## Edge Cases
- **DynamoDB / downstream outage while the app is up:** **not** caught by `/health` (liveness
  only). Those are covered by the reactive `dynamodb_*` and `api_lambda_errors` / `api_gw_5xx`
  alarms, not by this uptime probe.
- **Transient blip:** de-bouncing failed probes (e.g. alert only after N consecutive failures) is
  configured in the external monitor, not in this repo.
- **`/` requested:** returns `404` (the root path was removed); external monitors and smoke tests
  use `/health`.

## Acceptance Criteria
- [ ] `GET /health` is unauthenticated and returns `200 { "detail": "Healthy!" }` with no auth header.
- [ ] `GET /` returns `404` (root path removed).
- [ ] No AWS Route 53 health check or `HealthCheckStatus` CloudWatch alarm is provisioned for the API.

## Sources
`src/api/routes.py` (`health`), `docs/api/openapi_spec.yaml` (`/health`),
[BE-017](BE-017-feature-flags.md) (unauthenticated-endpoint precedent).
