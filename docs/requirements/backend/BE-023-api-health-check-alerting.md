# BE-023: API Health Check & Uptime Alerting

## Description
Provides a **proactive uptime alert** for the public API: if the API stops responding, an
alert is posted to the Discord ops channel — without waiting for real user traffic to surface
an error.

Two parts:

1. **Public health endpoint — `GET /health`.** An **unauthenticated** liveness endpoint (no
   Clerk authorizer, mirroring [BE-017](BE-017-feature-flags.md)'s `GET /feature-flags`) that
   returns `200 { "detail": "Healthy!" }` whenever the FastAPI app is running. It is
   **liveness-only** — it does not touch DynamoDB, S3, or any downstream dependency, so it
   reflects only whether the API itself is up and reachable. This replaces the former authed
   root `GET /` health check (the JWT authorizer made it un-probeable by an external monitor,
   which would get `401`, not `200`). The root path `/` no longer exists.

2. **Route 53 health check + CloudWatch alarm → Discord.** An AWS Route 53 health check probes
   `https://api.leagueql.com/health` over HTTPS every 30s. After **3 consecutive failures** it
   marks the endpoint unhealthy and drives `HealthCheckStatus` to `0` in CloudWatch
   (`AWS/Route53`, us-east-1). A CloudWatch metric alarm (`HealthCheckStatus < 1`) then routes
   through the existing `lambda_alerts` SNS topic → the `discord_notifier` Lambda, which renders
   the standard CloudWatch alarm payload as a red embed on `ALARM` and a green embed on `OK`
   (recovery). Effective time-to-alert on a real outage is ≈ 90s.

Only the **prod** environment is monitored, and the health check + alarm live in the **east
(us-east-1)** region only — Route 53 publishes its metrics exclusively to us-east-1, and the
east SNS topic (`aws_sns_topic.lambda_alerts`) is co-located there. This matches the existing
`prod` + `east` gating used for the DynamoDB / DLQ / EventBridge alarms.

No changes are needed on the Discord delivery side: the SNS topic, the Lambda subscription, and
the alarm-embed rendering already exist ([Discord notifier](../../../src/discord_notifier/handler.py)).

## Scope
- Endpoint: `src/api/routes.py` — `health()` handler at `GET /health` (returns `APIResponse(detail="Healthy!")`).
- API contract: `docs/api/openapi_spec.yaml` — the `/health` path with **no** `security` block
  and the standard `aws_proxy` integration to the API Lambda. The old `/` path is removed.
- Infrastructure: `infrastructure/regional/main.tf` — `aws_route53_health_check.api_health`
  (`fqdn = api.leagueql.com`, `resource_path = /health`, `type = HTTPS`, `request_interval = 30`,
  `failure_threshold = 3`) and `aws_cloudwatch_metric_alarm.api_health_unhealthy`
  (`namespace = AWS/Route53`, `metric_name = HealthCheckStatus`, `HealthCheckId` dimension,
  `alarm_actions`/`ok_actions` → `aws_sns_topic.lambda_alerts[0].arn`), both gated to
  `var.environment == "prod" && local.region == "east"`.
- Delivery (unchanged): `aws_sns_topic.lambda_alerts` → `module.discord_notifier_lambda`
  (`src/discord_notifier/handler.py`), webhook URL from SSM `/leagueql/<env>/discord/webhook_url`.

## Edge Cases
- **Transient blip (1–2 failed probes):** absorbed by the health check's `failure_threshold = 3`
  — the alarm does not fire on a single dropped request.
- **DynamoDB / downstream outage while the app is up:** **not** caught by `/health` (liveness
  only). Those are covered by the reactive `dynamodb_*` and `api_lambda_errors` / `api_gw_5xx`
  alarms, not by this uptime probe.
- **Metric stops reporting:** the alarm uses `treat_missing_data = "breaching"` so a total loss
  of the Route 53 metric also alerts, rather than silently masking an outage.
- **Non-prod / west region:** no health check or alarm is created (prod + east only).
- **`/` requested:** returns `404` (the root path was removed); external monitors and smoke
  tests use `/health`.
- **Recovery:** when the endpoint returns `200` again, the alarm returns to `OK` and a green
  recovery embed is posted (via `ok_actions`).

## Acceptance Criteria
- [ ] `GET /health` is unauthenticated and returns `200 { "detail": "Healthy!" }` with no auth header.
- [ ] `GET /` returns `404` (root path removed).
- [ ] The Route 53 health check probes `https://api.leagueql.com/health` every 30s and marks the
      endpoint unhealthy after 3 consecutive failures (prod/east only).
- [ ] When the endpoint is unhealthy, a red alarm embed is posted to the Discord ops channel via
      the existing `lambda_alerts` SNS topic; on recovery a green `OK` embed is posted.
- [ ] No Discord-notifier code changes are required for the alarm to render.

## Sources
`src/api/routes.py` (`health`), `docs/api/openapi_spec.yaml` (`/health`),
`infrastructure/regional/main.tf` (`aws_route53_health_check.api_health`,
`aws_cloudwatch_metric_alarm.api_health_unhealthy`, `aws_sns_topic.lambda_alerts`),
`src/discord_notifier/handler.py` (alarm embed rendering),
[BE-017](BE-017-feature-flags.md) (unauthenticated-endpoint precedent).
