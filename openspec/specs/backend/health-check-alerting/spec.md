# health-check-alerting Specification

## Purpose
Expose a public liveness endpoint for the API so an external uptime monitor can detect and alert on outages without waiting for real user traffic. Uptime probing and alerting are handled entirely by an external monitoring service (Better Stack) configured outside this repo; no AWS-side probe, alarm, application code, or Terraform is involved.

## Requirements

### Requirement: Public liveness endpoint
`GET /health` SHALL be unauthenticated and return `200 { "detail": "Healthy!" }` whenever the FastAPI app is running, touching no downstream dependency.

#### Scenario: Health probe
- **WHEN** `GET /health` is called with no auth header
- **THEN** it returns `200 { "detail": "Healthy!" }` without touching DynamoDB, S3, or any downstream dependency

### Requirement: Root path removed
`GET /` SHALL return `404` (the former authed root health check no longer exists).

#### Scenario: Root requested
- **WHEN** `GET /` is requested
- **THEN** it returns `404`

### Requirement: No AWS uptime infrastructure
No AWS Route 53 health check or `HealthCheckStatus` CloudWatch alarm SHALL be provisioned for the API.

#### Scenario: No AWS probe
- **WHEN** the infrastructure is provisioned
- **THEN** no Route 53 health check or `HealthCheckStatus` alarm exists for the API (uptime probing is delegated to the external monitor)
