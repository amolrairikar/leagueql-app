# BE-021: Async Chain OpenTelemetry Trace Propagation

## Description
Extends OpenTelemetry **distributed tracing** from the API Lambda ([BE-020](BE-020-api-otel-tracing.md))
through the **async onboarding chain** so an onboard/refresh is a **single end-to-end trace** in
Axiom: browser ([FE-029](../frontend/FE-029-frontend-observability.md)) → API → **Onboarder** →
**Processor**, and likewise the scheduled Sleeper auto-refresh ([BE-012](BE-012-scheduled-sleeper-auto-refresh.md))
→ Onboarder → Processor. Previously the chain was explicitly out of scope and ran on
`correlation_id`-only logging, so the trace ended at the API span and the backend work never
appeared in the waterfall.

Trace context is propagated by **parent-child continuation** (the same `trace_id` flows across each
hop), *not* span links — the onboarder/processor spans are children of the originating span. This
rides the two carriers that `correlation_id` already uses:

1. **The async Lambda invoke payload** — `invoke_onboarder` (API→Onboarder, Sleeper-Refresh→Onboarder).
2. **The S3 `manifest.json` object user-metadata** — the Onboarder writes it, an `s3:ObjectCreated`
   event triggers the Processor, which reads it back (Onboarder→Processor).

Each chain Lambda becomes its own OTel **service** — `leagueql-onboarder`, `leagueql-processor`,
`leagueql-sleeper-refresh` — joined to `leagueql-api` by `trace_id` (services stay separate; they
are *not* merged into one `service.name`). `botocore` + `requests` are instrumented so DynamoDB/S3
calls show as child spans. Because `common/logging_utils.py` already adds `trace_id`/`span_id` to
JSON logs when a span is active, the chain Lambdas' CloudWatch logs gain `trace_id` automatically
once OTel is bundled, enabling log↔trace pivoting for the whole flow.

Tracing remains gated on Axiom config (token in SSM + dataset) and is a **true no-op** when
unconfigured. The existing lightweight `correlation_id` mechanism is **unchanged and preserved** on
every hop — trace context is purely additive.

## Scope
- **Shared bootstrap:** `src/common/tracing.py` (vendored into every Lambda zip) provides:
  `is_enabled()`, `build_provider(service_name)` (`TracerProvider` with
  `service.name`/`deployment.environment`, `BatchSpanProcessor` → `OTLPSpanExporter` to
  `AXIOM_TRACES_URL` with `Authorization: Bearer <token>` + `X-Axiom-Dataset`, and
  `Botocore`/`Requests` instrumentation), `init_tracing(service_name)` (idempotent, gated, fail-safe
  no-op), `inject_context(carrier)` / `extract_context(carrier)` (W3C `TraceContextTextMapPropagator`),
  and a `traced_handler(span_name, *, carrier, root)` contextmanager that starts a continuation (or
  root) span and `force_flush`es per invocation.
- **API** ([BE-020](BE-020-api-otel-tracing.md)): `src/api/telemetry.py` reuses
  `common.tracing.build_provider("leagueql-api")`; FastAPI instrumentation + the flush middleware
  stay in `telemetry.py`. API runtime behavior is unchanged.
- **Carrier #1 (invoke payload):** `src/common/onboarder_invoke.py` adds
  `payload["trace_context"] = inject_context({})` (empty `{}` when tracing off).
- **Onboarder:** `src/onboarder/handler.py` calls `init_tracing("leagueql-onboarder")` and wraps the
  handler in `traced_handler("onboarder.handle", carrier=event.get("trace_context"))`.
- **Carrier #2 (S3 metadata):** `src/onboarder/writer.py` calls `inject_context(metadata)` so
  `traceparent`/`tracestate` ride the `manifest.json` object metadata next to `correlation_id`.
- **Processor:** `src/processor/handler.py` calls `init_tracing("leagueql-processor")` and wraps the
  work in `traced_handler("processor.handle", carrier=manifest_metadata)`.
- **Sleeper Refresh:** `src/sleeper_refresh/handler.py` calls `init_tracing("leagueql-sleeper-refresh")`
  and wraps each per-league refresh in `traced_handler("sleeper_refresh.league", root=True)` (cron
  has no inbound context) before invoking the onboarder.
- **Dependencies:** `opentelemetry-api`, `opentelemetry-sdk`, `opentelemetry-exporter-otlp-proto-http`,
  `opentelemetry-instrumentation-botocore`, `opentelemetry-instrumentation-requests` added to
  `src/onboarder/requirements.txt`, `src/processor/requirements.txt`, `src/sleeper_refresh/requirements.txt`.
- **Infra:** `AXIOM_API_TOKEN_SSM_PARAM`, `AXIOM_DATASET`, `AXIOM_TRACES_URL`, `ENVIRONMENT` env vars
  on the onboarder/processor/sleeper_refresh Lambdas (`infrastructure/regional/main.tf`); the
  `ssm:GetParameter` grant on `/leagueql/{env}/axiom/api_token` added to each of their roles
  (`infrastructure/global/{dev,prod}/main.tf`).

## Edge Cases
- **Tracing not configured** (no `AXIOM_API_TOKEN_SSM_PARAM`/`AXIOM_DATASET`): `init_tracing` is a
  no-op, `inject_context` returns `{}`, `extract_context` returns `None`, `traced_handler` is a bare
  pass-through. Zero network calls — the default for unit tests, the Behave suite, and unconfigured
  envs; the chain behaves exactly as before (`correlation_id` only).
- **Export failure / Axiom unreachable:** must never affect the chain. Init, inject, extract, span
  start, and `force_flush` all swallow their own errors; a job still completes and writes its
  JOB_STATUS.
- **Missing/invalid carrier** at any hop: the handler starts a fresh root trace (normal OTel); no
  error. (E.g. a manifest written before this change, or a re-driven S3 event.)
- **Async time-gap in the waterfall is expected:** the parent (API/onboarder) span has ended and
  been exported before the child Lambda runs; Axiom stitches by `trace_id` + `parent_span_id`. Minor
  inter-Lambda clock skew is a cosmetic waterfall artifact.
- **Lambda freeze between invocations:** spans are `force_flush`ed per invocation so they aren't
  stranded in a frozen execution environment.
- **`correlation_id` preserved:** still set/propagated identically on both carriers; `trace_id` is
  added, never a replacement.
- **Known coverage gaps (acceptable; optional follow-ups):**
  - The Onboarder fetches league data via **`aiohttp`** (`sleeper_client.py`, `espn_client.py`),
    which the `requests` instrumentor does not cover — those outbound ESPN/Sleeper calls won't appear
    as spans (the onboarder span and its botocore S3/DDB children still do). Could add
    `opentelemetry-instrumentation-aiohttp-client` later.
  - The Processor does parallel work in a `ThreadPoolExecutor`; OTel context isn't auto-copied into
    worker threads, so DynamoDB/S3 calls made inside the pool may not attach to `processor.handle`.
    The top-level span still continues the trace. Could copy `contextvars` into the pool later.

## Acceptance Criteria
- [ ] With Axiom configured, an onboard from the app produces **one** trace whose `trace_id` spans
      `leagueql-api` → `leagueql-onboarder` → `leagueql-processor`, including botocore child spans for
      DynamoDB/S3 and the API→onboarder Lambda Invoke.
- [ ] A scheduled Sleeper auto-refresh produces `leagueql-sleeper-refresh` root traces that continue
      into the onboarder and processor.
- [ ] Onboarder/processor/sleeper-refresh CloudWatch JSON logs include a non-empty `trace_id` during
      a traced invocation, and `correlation_id` still appears unchanged.
- [ ] With no Axiom config (tests / unconfigured env), `init_tracing` installs nothing, the helpers
      make no network calls, and the chain behaves exactly as before; the Behave component suite passes.
- [ ] An Axiom export error (or any tracing failure) never changes a job's outcome — the chain still
      completes and writes JOB_STATUS.
- [ ] dev and prod export to `leagueql-dev` / `leagueql-prod`; the token is read from SSM and never
      present in env vars / TF state / CI.

## Sources
`src/common/tracing.py`, `src/api/telemetry.py`, `src/common/onboarder_invoke.py`,
`src/onboarder/handler.py`, `src/onboarder/writer.py`, `src/processor/handler.py`,
`src/sleeper_refresh/handler.py`, `src/common/logging_utils.py`, `src/common/secrets.py`,
`src/onboarder/requirements.txt`, `src/processor/requirements.txt`,
`src/sleeper_refresh/requirements.txt`, `infrastructure/regional/main.tf`,
`infrastructure/global/{dev,prod}/main.tf`.
