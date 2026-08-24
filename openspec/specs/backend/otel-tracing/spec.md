# otel-tracing Specification

## Purpose
Add OpenTelemetry distributed tracing to the backend, exporting spans to Better Stack over OTLP/HTTP so a browser action becomes a single end-to-end trace: browser → API → onboarder → processor (and the scheduled Sleeper auto-refresh → onboarder → processor). Each chain Lambda is its own OTel service joined by `trace_id`. Tracing is additive to the existing `correlation_id`, runs in prod only, and is a true no-op when unconfigured.

## Requirements

### Requirement: Produce API server spans
With Better Stack configured, an API request SHALL produce a `leagueql-api` server span with child spans for its DynamoDB/HTTP calls.

#### Scenario: API request traced
- **WHEN** the API Lambda handles a request and tracing is configured
- **THEN** it emits a `leagueql-api` server span with botocore/requests child spans for the DynamoDB and outbound HTTP calls it makes

#### Scenario: Continue an incoming trace
- **WHEN** a request carries a valid `traceparent` header
- **THEN** the request span continues that trace (same `trace_id`) rather than starting a new one

### Requirement: Continue the trace through the async chain
Trace context SHALL propagate by parent-child continuation across API → onboarder → processor and sleeper-refresh → onboarder → processor, keeping one `trace_id` while each Lambda stays its own service.

#### Scenario: One trace across the onboard chain
- **WHEN** an onboard runs with tracing configured
- **THEN** one trace whose `trace_id` spans `leagueql-api` → `leagueql-onboarder` → `leagueql-processor` is produced, including botocore child spans and the API→onboarder Invoke

#### Scenario: Scheduled refresh trace
- **WHEN** the scheduled Sleeper auto-refresh runs
- **THEN** it produces `leagueql-sleeper-refresh` root traces that continue into the onboarder and processor

### Requirement: Cross-link logs with trace IDs
Every JSON log line emitted during a traced request/invocation SHALL include a non-empty `trace_id`, with `correlation_id` unchanged.

#### Scenario: Logs carry trace_id
- **WHEN** a traced request/invocation logs across the API, onboarder, processor, and sleeper-refresh
- **THEN** each log line includes a non-empty `trace_id` and the existing `correlation_id` still appears

### Requirement: No-op when unconfigured
With no tracing config, `init_tracing` SHALL install nothing, the helpers SHALL make no network calls, and the API and chain SHALL behave exactly as before.

#### Scenario: Unconfigured environment
- **WHEN** no OTLP endpoint/token is configured (unit tests, Behave suite, dev)
- **THEN** `init_tracing` is a no-op, `inject_context` returns `{}`, `extract_context` returns `None`, `traced_handler` is a pass-through, zero network calls are made, and the component suite passes

### Requirement: Tracing failures never affect behavior
A Better Stack export error or any tracing failure SHALL NOT change an endpoint's status code/body or a job's outcome.

#### Scenario: Export failure
- **WHEN** Better Stack is unreachable or any tracing step errors
- **THEN** the error is swallowed, the endpoint response is unchanged, and the job still completes and writes its `JOB_STATUS`

#### Scenario: Missing/invalid incoming context
- **WHEN** a hop receives a missing or invalid `traceparent`/carrier
- **THEN** it starts a fresh root trace without error

### Requirement: Prod-only export with secret token from SSM
Tracing SHALL export only in prod, with dev untraced, and the OTLP token SHALL be read from SSM at runtime, never landing in env vars, Terraform state, or CI.

#### Scenario: Prod vs dev
- **WHEN** the Lambdas run in prod (endpoint set) versus dev (empty endpoint)
- **THEN** prod exports to the Better Stack source while dev short-circuits to a no-op (no export/SSM call), and the token is read from SSM by parameter name only
