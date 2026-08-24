# observability Specification

## Purpose
Add browser-side observability to the React app, exported to Better Stack: distributed tracing via the OpenTelemetry Web SDK (document-load, route-change, and per-API-call fetch spans), RUM/Web Vitals, and error capture on spans. The browser exporter posts OTLP to a same-origin `/ingest/traces` proxy that injects the source token server-side, so no token is ever shipped to the browser. Runs in prod only.

## Requirements

### Requirement: Emit browser trace and Web Vitals spans
With `VITE_TRACES_URL` set (non-test), the app SHALL emit a document-load span, Web Vitals spans, and route-change spans.

#### Scenario: Spans emitted
- **WHEN** the app loads and navigates with `VITE_TRACES_URL` configured
- **THEN** it emits a document-load span, Core Web Vitals spans (LCP, CLS, INP, FCP, TTFB), and route-change spans, attributed with the Clerk user id (once known), `service.name=leagueql-frontend`, and `deployment.environment`

### Requirement: Link browser spans to the API trace
An API call SHALL carry a `traceparent` header only to the API origin so the browser span shares a trace id with the API Lambda span.

#### Scenario: End-to-end trace
- **WHEN** the app makes a call to the API origin
- **THEN** a `traceparent` header is injected (only for the API origin, never third parties) and the resulting browser span shares a trace id with the API Lambda server span

### Requirement: Capture render errors on spans
A render error caught by `ErrorBoundary` SHALL be recorded as an exception and still logged, without introducing a global error store.

#### Scenario: Error captured
- **WHEN** `ErrorBoundary` catches a render error
- **THEN** the exception is recorded on a span and still logged to console, with no global error banner/store introduced

### Requirement: No token in the browser and no CSP change
No Better Stack token SHALL appear in the client bundle; the exporter SHALL target only same-origin `/ingest/traces`, leaving the CSP unchanged.

#### Scenario: Token absent, same-origin target
- **WHEN** the built bundle and network are inspected
- **THEN** no source token appears; the exporter targets only same-origin `/ingest/traces` (the proxy injects the token server-side), and the CSP in `public/_headers` is unchanged with no violations

### Requirement: No-op in tests and safe on failure
Telemetry init SHALL be a no-op under Vitest or when unconfigured, and exporter/proxy failures SHALL never break the UI.

#### Scenario: Test environment
- **WHEN** the app runs under Vitest or with `VITE_TRACES_URL` unset
- **THEN** telemetry init does nothing and no telemetry network request is made (MSW `onUnhandledRequest: 'error'` does not trip)

#### Scenario: Exporter failure
- **WHEN** the exporter or proxy fails
- **THEN** span export errors are swallowed and the app renders and functions identically
