# BE-020: API OpenTelemetry Tracing → Axiom

## Description
Adds OpenTelemetry **distributed tracing** to the **API Lambda only** (`src/api`, the FastAPI app
behind Mangum), exporting spans to **Axiom** over OTLP/HTTP. Each incoming request produces a server
span (via FastAPI auto-instrumentation) with child spans for downstream calls — DynamoDB/Lambda
(`botocore`) and outbound HTTP (`requests`). When the browser sends a `traceparent` header
([FE-029](../frontend/FE-029-frontend-observability.md)), the request span **continues that trace**,
giving a single end-to-end trace from the browser through API Gateway into the Lambda.

This partially reverses the earlier full removal of OTel: it re-introduces OTel scoped to Axiom
(not Honeycomb), starting with the API Lambda. Trace context is propagated **onward through the
async onboarding chain (Onboarder → Processor) and the Sleeper auto-refresh** under
[BE-021](BE-021-async-chain-otel-propagation.md), so an onboard is a single end-to-end trace; the
chain continues to also carry the lightweight `correlation_id` (`ContextVar` in JSON logs)
mechanism. The API Lambda continues to log `correlation_id` exactly as before; additionally the
active `trace_id` is added to every JSON log line so a trace in Axiom can be pivoted to its
CloudWatch logs and vice-versa.

Tracing runs in **both dev and prod**, isolated by Axiom dataset (`leagueql-dev` / `leagueql-prod`).
The Axiom ingest token is sensitive and is fetched at runtime from SSM Parameter Store by parameter
*name* (same pattern as the Stripe secret key, BE-015) — the value never lands in a Lambda env var,
Terraform state, or CI.

## Scope
- Tracing init: `src/api/telemetry.py::init_tracing(app)`. The provider/exporter and
  `botocore`/`requests` instrumentation are built by the shared `src/common/tracing.py::build_provider`
  (`service.name=leagueql-api`, `deployment.environment={env}`, `BatchSpanProcessor` →
  `OTLPSpanExporter` (HTTP) to `AXIOM_TRACES_URL` with `Authorization: Bearer <token>` +
  `X-Axiom-Dataset: <AXIOM_DATASET>`); `telemetry.py` adds the FastAPI-specific
  `FastAPIInstrumentor.instrument_app(app)` on top. See [BE-021](BE-021-async-chain-otel-propagation.md)
  for the shared module.
- Wiring: `src/api/main.py` calls `init_tracing(app)` after the app is built, before `Mangum`.
- Token: fetched via `src/common/secrets.py::get_secret_from_env_param("AXIOM_API_TOKEN_SSM_PARAM")`.
- Log cross-linking: `src/common/logging_utils.py::JsonFormatter` adds `trace_id` (and `span_id`)
  when a span is active; `correlation_id` is unchanged.
- Per-request span flush before the Lambda response returns (Lambda freezes between invocations).
- Dependencies: `opentelemetry-api`, `opentelemetry-sdk`, `opentelemetry-exporter-otlp-proto-http`,
  `opentelemetry-instrumentation-fastapi`, `opentelemetry-instrumentation-botocore`,
  `opentelemetry-instrumentation-requests` in `Pipfile` + `src/api/requirements.txt`.
- Infra: `AXIOM_API_TOKEN_SSM_PARAM`, `AXIOM_DATASET`, `AXIOM_TRACES_URL` env vars on the API Lambda
  (`infrastructure/regional/main.tf`); `ssm:GetParameter` grant on `/leagueql/{env}/axiom/api_token`
  in the API role (`infrastructure/global/{dev,prod}/main.tf`); `traceparent`/`tracestate` added to
  API Gateway CORS allow-headers (`infrastructure/modules/api-gw/main.tf`).

## Edge Cases
- **Tracing not configured** (no `AXIOM_API_TOKEN_SSM_PARAM`, or the SSM fetch returns `""`):
  `init_tracing` is a **no-op** — no provider/exporter is installed. This is the default for unit
  tests, the Behave component suite, and any unconfigured environment, so they make zero network
  calls and behave identically to before.
- **Export failure / Axiom unreachable:** must never affect the API response. The exporter swallows
  its own errors; instrumentation never raises into the request path.
- **Missing/invalid incoming `traceparent`:** the request starts a fresh root trace (normal OTel
  behavior); no error.
- **Lambda freeze between invocations:** spans are force-flushed per request so they are not stranded
  in a frozen execution environment and lost.
- **Cold-start latency:** the SSM token fetch happens once per execution environment (cached); it
  must not be on the hot path of every request.
- **Scope:** this doc covers the API Lambda. The async onboarding chain (Onboarder → Processor) and
  the Sleeper auto-refresh continue the trace under [BE-021](BE-021-async-chain-otel-propagation.md).
  The Stripe webhook and other Lambdas remain on `correlation_id`-only.
- **`correlation_id` preserved:** existing log correlation for the onboard/refresh chain is unchanged;
  `trace_id` is *added*, not a replacement.

## Acceptance Criteria
- [ ] With Axiom configured, a request to the API Lambda produces a server span in the env's dataset
      with child spans for DynamoDB/HTTP calls it makes.
- [ ] A request carrying a valid `traceparent` continues the caller's trace (same trace id) rather
      than starting a new one.
- [ ] Every JSON log line emitted during a traced request includes a non-empty `trace_id`, and
      `correlation_id` still appears unchanged.
- [ ] With no Axiom config (tests / unconfigured env), `init_tracing` installs nothing, makes no
      network calls, and the API behaves exactly as before; the Behave component suite passes.
- [ ] An Axiom export error does not change any endpoint's status code or body.
- [ ] dev and prod export to `leagueql-dev` / `leagueql-prod` respectively; the token is read from
      SSM and never present in env vars / TF state / CI.

## Sources
`src/api/telemetry.py`, `src/api/main.py`, `src/common/logging_utils.py`, `src/common/secrets.py`,
`Pipfile`, `src/api/requirements.txt`, `infrastructure/regional/main.tf`,
`infrastructure/global/{dev,prod}/main.tf`, `infrastructure/modules/api-gw/main.tf`,
`OTEL_IMPLEMENTATION_PLAN.md`.
