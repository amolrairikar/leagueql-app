# BE-020: Backend OpenTelemetry Tracing → Better Stack

## Description
Adds OpenTelemetry **distributed tracing** to the backend, exporting spans to **Better Stack** over
OTLP/HTTP, so a browser action becomes a **single end-to-end trace**: browser
([FE-029](../frontend/FE-029-frontend-observability.md)) → **API** → **Onboarder** →
**Processor** (and likewise the scheduled Sleeper auto-refresh
([BE-012](BE-012-scheduled-sleeper-auto-refresh.md)) → Onboarder → Processor). This doc covers
tracing across **every backend Lambda in the onboarding chain** — it began as API-only and was
extended through the async chain; both increments now share one bootstrap
(`src/common/tracing.py`) and are described here together.

Each incoming API request produces a server span (FastAPI auto-instrumentation) with child spans
for downstream DynamoDB/Lambda (`botocore`) and outbound HTTP (`requests`). When the browser sends
a `traceparent` header the request span **continues that trace**. Trace context is then propagated
**onward through the async chain by parent-child continuation** (the same `trace_id` flows across
each hop; onboarder/processor spans are children of the originating span — *not* span links), so an
onboard/refresh is one continuous waterfall rather than ending at the API span.

Each chain Lambda is its own OTel **service** — `leagueql-api`, `leagueql-onboarder`,
`leagueql-processor`, `leagueql-sleeper-refresh` — joined by `trace_id` (services stay separate;
they are *not* merged into one `service.name`). Because `common/logging_utils.py` adds
`trace_id`/`span_id` to JSON logs when a span is active, every chain Lambda's CloudWatch logs gain
`trace_id` automatically, enabling log↔trace pivoting for the whole flow. The existing lightweight
`correlation_id` mechanism is **unchanged and preserved** on every hop — trace context is purely
additive.

Tracing runs in **prod only** — the Better Stack free tier provides a single OTLP source, dedicated
to prod (spans carry `deployment.environment = prod`). **Dev runs untraced:** its endpoint env var
is empty, so `is_enabled()` short-circuits to `False` and the dev Lambdas make zero export/SSM calls
(the standard no-op path). The Better Stack OTLP source token is sensitive and is fetched at runtime
from SSM Parameter Store by parameter *name* — the value never lands in a Lambda env var, Terraform
state, or CI. Tracing is gated on the endpoint + token being configured and is a **true no-op** when
unconfigured.

## Scope
- **Shared bootstrap — `src/common/tracing.py`** (vendored into every Lambda zip):
  - `is_enabled()`, `build_provider(service_name)` — a `TracerProvider` with
    `service.name`/`deployment.environment`, `BatchSpanProcessor` → `OTLPSpanExporter` (HTTP) to
    `OTEL_EXPORTER_OTLP_TRACES_ENDPOINT` with `Authorization: Bearer <token>` (Better Stack has no
    dataset header), and `Botocore`/`Requests` instrumentation so DynamoDB/S3 and outbound HTTP show
    as child spans.
  - `init_tracing(service_name)` — idempotent, gated, fail-safe no-op.
  - `inject_context(carrier)` / `extract_context(carrier)` — W3C `TraceContextTextMapPropagator`.
  - `traced_handler(span_name, *, carrier, root)` — a contextmanager that starts a continuation
    (or root) span and `force_flush`es per invocation.
- **API** (`src/api`, the FastAPI app behind Mangum): `src/api/telemetry.py::init_tracing(app)`
  reuses `common.tracing.build_provider("leagueql-api")` and adds the FastAPI-specific
  `FastAPIInstrumentor.instrument_app(app)` plus a per-request span-flush middleware.
  `src/api/main.py` calls it after the app is built, before `Mangum`.
- **Carrier #1 — async invoke payload:** `src/common/onboarder_invoke.py` adds
  `payload["trace_context"] = inject_context({})` (empty `{}` when tracing off) on
  API→Onboarder and Sleeper-Refresh→Onboarder invokes.
- **Onboarder:** `src/onboarder/handler.py` calls `init_tracing("leagueql-onboarder")` and wraps the
  handler in `traced_handler("onboarder.handle", carrier=event.get("trace_context"))`.
- **Carrier #2 — S3 metadata:** `src/onboarder/writer.py` calls `inject_context(metadata)` so
  `traceparent`/`tracestate` ride the `manifest.json` object user-metadata next to `correlation_id`;
  an `s3:ObjectCreated` event triggers the Processor, which reads it back.
- **Processor:** `src/processor/handler.py` calls `init_tracing("leagueql-processor")` and wraps the
  work in `traced_handler("processor.handle", carrier=manifest_metadata)`.
- **Sleeper Refresh:** `src/sleeper_refresh/handler.py` calls
  `init_tracing("leagueql-sleeper-refresh")` and wraps each per-league refresh in
  `traced_handler("sleeper_refresh.league", root=True)` (cron has no inbound context) before
  invoking the onboarder.
- **Log cross-linking:** `src/common/logging_utils.py::JsonFormatter` adds `trace_id` (and
  `span_id`) when a span is active; `correlation_id` is unchanged.
- **Token:** `src/common/secrets.py::get_secret_from_env_param("OTEL_EXPORTER_TOKEN_SSM_PARAM")`.
- **Dependencies:** `opentelemetry-api`, `opentelemetry-sdk`,
  `opentelemetry-exporter-otlp-proto-http`, `opentelemetry-instrumentation-fastapi` (API only),
  `opentelemetry-instrumentation-botocore`, `opentelemetry-instrumentation-requests` — in `Pipfile`,
  `src/api/requirements.txt`, `src/onboarder/requirements.txt`, `src/processor/requirements.txt`,
  and `src/sleeper_refresh/requirements.txt`.
- **Infra:** `OTEL_EXPORTER_TOKEN_SSM_PARAM`, `OTEL_EXPORTER_OTLP_TRACES_ENDPOINT` (+ `ENVIRONMENT`)
  env vars on the API/onboarder/processor/sleeper_refresh Lambdas (`infrastructure/regional/main.tf`).
  The endpoint comes from the `local.betterstack_otlp_traces_endpoint` prod-conditional — the real
  ingesting host on prod, `""` on dev (so dev short-circuits to a no-op). The host is **non-sensitive**
  (auth is the Bearer source token), so it's committed rather than passed as a secret; only the token
  is secret. The `ssm:GetParameter` grant on `/leagueql/{env}/betterstack/source_token` is added to
  each role (`infrastructure/global/{dev,prod}/main.tf`; the dev grant is inert — no dev token param
  is created). `traceparent`/`tracestate` added to API Gateway CORS allow-headers
  (`infrastructure/modules/api-gw/main.tf`).

## Edge Cases
- **Tracing not configured** (no `OTEL_EXPORTER_OTLP_TRACES_ENDPOINT`/`OTEL_EXPORTER_TOKEN_SSM_PARAM`,
  or the SSM fetch returns `""`): `init_tracing` is a no-op, `inject_context` returns `{}`, `extract_context` returns
  `None`, `traced_handler` is a bare pass-through. Zero network calls — the default for unit tests,
  the Behave component suite, and any unconfigured env; the API and chain behave exactly as before
  (`correlation_id` only).
- **Export failure / Better Stack unreachable:** must never affect the API response or the chain. Init,
  inject, extract, span start, `force_flush`, and the exporter all swallow their own errors;
  instrumentation never raises into the request path, and a job still completes and writes its
  JOB_STATUS.
- **Missing/invalid incoming `traceparent` or carrier** at any hop: the handler starts a fresh root
  trace (normal OTel behavior); no error. (E.g. a manifest written before this change, or a
  re-driven S3 event.)
- **Async time-gap in the waterfall is expected:** the parent (API/onboarder) span has ended and
  been exported before the child Lambda runs; Better Stack stitches by `trace_id` + `parent_span_id`. Minor
  inter-Lambda clock skew is a cosmetic waterfall artifact.
- **Lambda freeze between invocations:** spans are `force_flush`ed per invocation/request so they
  are not stranded in a frozen execution environment and lost.
- **Cold-start latency:** the SSM token fetch happens once per execution environment (cached); it
  must not be on the hot path of every request.
- **`correlation_id` preserved:** existing log correlation is unchanged on both carriers; `trace_id`
  is *added*, never a replacement.
- **Known coverage gaps (acceptable; optional follow-ups):**
  - The Onboarder fetches league data via **`aiohttp`** (`sleeper_client.py`, `espn_client.py`),
    which the `requests` instrumentor does not cover — those outbound ESPN/Sleeper calls won't
    appear as spans (the onboarder span and its botocore S3/DDB children still do). Could add
    `opentelemetry-instrumentation-aiohttp-client` later.
  - The Processor does parallel work in a `ThreadPoolExecutor`; OTel context isn't auto-copied into
    worker threads, so DynamoDB/S3 calls made inside the pool may not attach to `processor.handle`.
    The top-level span still continues the trace. Could copy `contextvars` into the pool later.

## Acceptance Criteria
- [ ] With Better Stack configured, a request to the API Lambda produces a `leagueql-api` server span
      in the env's source with child spans for the DynamoDB/HTTP calls it makes.
- [ ] A request carrying a valid `traceparent` continues the caller's trace (same trace id) rather
      than starting a new one.
- [ ] With Better Stack configured, an onboard from the app produces **one** trace whose `trace_id` spans
      `leagueql-api` → `leagueql-onboarder` → `leagueql-processor`, including botocore child spans
      for DynamoDB/S3 and the API→onboarder Lambda Invoke.
- [ ] A scheduled Sleeper auto-refresh produces `leagueql-sleeper-refresh` root traces that continue
      into the onboarder and processor.
- [ ] Every JSON log line emitted during a traced request/invocation across the API, onboarder,
      processor, and sleeper-refresh includes a non-empty `trace_id`, and `correlation_id` still
      appears unchanged.
- [ ] With no tracing config (tests / unconfigured env), `init_tracing` installs nothing, the helpers
      make no network calls, and both the API and the chain behave exactly as before; the Behave
      component suite passes.
- [ ] A Better Stack export error (or any tracing failure) never changes an endpoint's status code/body,
      nor a job's outcome — the chain still completes and writes JOB_STATUS.
- [ ] prod exports to the Better Stack source; dev runs untraced (empty endpoint → `is_enabled()`
      False → no export/SSM call). The token is read from SSM and never present in env vars / TF state / CI.

## Sources
`src/common/tracing.py`, `src/api/telemetry.py`, `src/api/main.py`,
`src/common/onboarder_invoke.py`, `src/onboarder/handler.py`, `src/onboarder/writer.py`,
`src/processor/handler.py`, `src/sleeper_refresh/handler.py`, `src/common/logging_utils.py`,
`src/common/secrets.py`, `Pipfile`, `src/api/requirements.txt`, `src/onboarder/requirements.txt`,
`src/processor/requirements.txt`, `src/sleeper_refresh/requirements.txt`,
`infrastructure/regional/main.tf` (`local.betterstack_otlp_traces_endpoint`),
`infrastructure/global/{dev,prod}/main.tf`, `infrastructure/modules/api-gw/main.tf`,
`OTEL_IMPLEMENTATION_PLAN.md`.
