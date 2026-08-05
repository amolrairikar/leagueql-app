# FE-029: Frontend Observability (OpenTelemetry + RUM → Better Stack)

## Description
Adds browser-side observability to the React app, exported to **Better Stack**:
- **Distributed tracing** via the OpenTelemetry Web SDK — a document-load span on initial load,
  route-change spans, and a `fetch` span for every API call. The fetch instrumentation injects a
  `traceparent` header **only** on calls to the API origin, so browser spans link to the API Lambda
  server span ([BE-020](../backend/BE-020-backend-otel-tracing.md)) into one end-to-end trace.
- **RUM / Web Vitals** — Core Web Vitals (LCP, CLS, INP, FCP, TTFB) are captured with the
  `web-vitals` library and emitted as short spans (value + rating as attributes), with dashboards
  built in Better Stack from that data.
- **Error capture** — the existing `ErrorBoundary`/`logger` additionally record the exception on a
  span. No global error store is introduced (the inline-error-handling pattern is preserved).

Spans are attributed with the signed-in Clerk user id once known (`user.id`), `service.name`
(`leagueql-frontend`), and `deployment.environment`.

**Token handling (no secret in the browser):** the browser exporter posts OTLP to a **same-origin
`/ingest/traces`** endpoint served by the Cloudflare deployment; that proxy injects the Better Stack
source token server-side and forwards to Better Stack. A `VITE_`-prefixed token would be inlined into
the client bundle and readable by any user, so **no token is ever shipped to the browser**. Because
the exporter target is same-origin, the existing CSP (`connect-src 'self'`) already covers it — **no
CSP change is required**.

Runs in **prod only** — the single Cloudflare/worker deploy serves prod, and the Better Stack free
tier provides one source. The destination is set on that deploy via the worker's `OTEL_TRACES_URL`
var + `OTEL_EXPORTER_TOKEN` secret, not in client code; without both, the proxy acks `204` and no
traces flow.

## Scope
- Init: `frontend/src/lib/telemetry.ts::initTelemetry()` — `WebTracerProvider` + `ZoneContextManager`
  + `BatchSpanProcessor` → `OTLPTraceExporter` (url = `VITE_TRACES_URL`, default `/ingest/traces`);
  `FetchInstrumentation` (`propagateTraceHeaderCorsUrls` = API base URL) and
  `DocumentLoadInstrumentation`; `web-vitals` callbacks → spans.
- Bootstrap: called from `frontend/src/app/main.tsx` before `createRoot`.
- User attribution: `frontend/src/app/auth-token-bridge.tsx` sets the user id once Clerk loads.
- Route-change spans + error capture: `frontend/src/app/app.tsx`, `frontend/src/lib/logger.ts` /
  `frontend/src/components/error-boundary.tsx`.
- Proxy: a Cloudflare Worker (`workers/leagueql-app/index.js`) wired via root `wrangler.jsonc` (`main` +
  `ASSETS` binding) that handles `POST /ingest/traces` and otherwise serves the static SPA assets.
- Packages: `@opentelemetry/api`, `@opentelemetry/sdk-trace-web`,
  `@opentelemetry/exporter-trace-otlp-http`, `@opentelemetry/instrumentation-fetch`,
  `@opentelemetry/instrumentation-document-load`, `@opentelemetry/context-zone`,
  `@opentelemetry/resources`, `@opentelemetry/semantic-conventions`, `web-vitals`.
- Config: prod builds default the exporter URL to `/ingest/traces` (no build var needed);
  other builds opt in via `VITE_TRACES_URL` (e.g. `.env.local` for local dev). The Worker reads
  `OTEL_TRACES_URL` (committed in `wrangler.jsonc` `vars`) + `OTEL_EXPORTER_TOKEN` (Worker secret);
  it forwards only when both are set (otherwise acks `204`).

## Edge Cases
- **Not configured / test env:** telemetry init is a **no-op** when `VITE_TRACES_URL` is unset **or**
  when running under Vitest (`import.meta.env.VITE_API_URL === 'http://test.local'`). This is
  required because MSW runs with `onUnhandledRequest: 'error'` — any stray telemetry request would
  fail the component tests. Local `npm run dev` is also off unless explicitly pointed at a proxy.
- **No token in client:** the browser holds no source token; it lives only as a Cloudflare secret on
  the proxy. Inspecting the bundle/network reveals only same-origin `/ingest/traces`.
- **`traceparent` scoping:** the header is injected only for the API origin
  (`propagateTraceHeaderCorsUrls`), never for third parties (Clerk, images).
- **Exporter/proxy failure:** must never break the UI — span export errors are swallowed; the app
  renders and functions identically with telemetry down.
- **CSP:** same-origin exporter means no `connect-src` change ([FE-024](FE-024-security-headers.md)
  unaffected). The proxy's outbound call to the Better Stack ingesting host happens server-side,
  outside CSP.
- **API client untouched:** `FetchInstrumentation` wraps native `fetch`, which `api-client.ts`
  already uses; request dedup/caching behavior is unchanged.

## Acceptance Criteria
- [ ] With `VITE_TRACES_URL` set (non-test), loading the app emits a document-load span and Web
      Vitals spans to Better Stack; navigating between routes emits route-change spans.
- [ ] An API call carries a `traceparent` header to the API origin and the resulting browser span
      shares a trace id with the API Lambda server span (end-to-end trace).
- [ ] A render error caught by `ErrorBoundary` is recorded as an exception (and still logged to
      console); no global error banner/store is introduced.
- [ ] Under Vitest, telemetry init does nothing and no telemetry network request is made (MSW
      `onUnhandledRequest: 'error'` does not trip); all existing component tests pass.
- [ ] No Better Stack token appears anywhere in the built client bundle; the exporter targets
      only same-origin `/ingest/traces`.
- [ ] The CSP in `frontend/public/_headers` is unchanged and the app loads without CSP violations.

## Sources
`frontend/src/lib/telemetry.ts`, `frontend/src/app/main.tsx`,
`frontend/src/app/auth-token-bridge.tsx`, `frontend/src/app/app.tsx`, `frontend/src/lib/logger.ts`,
`frontend/src/components/error-boundary.tsx`, `workers/leagueql-app/index.js`, `wrangler.jsonc`,
`frontend/vite.config.ts`, `OTEL_IMPLEMENTATION_PLAN.md`.
