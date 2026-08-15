/**
 * Frontend observability — OpenTelemetry tracing + Web Vitals → Better Stack (FE-029).
 *
 * Spans are exported (OTLP/HTTP) to a **same-origin** `/ingest/traces` proxy
 * (`VITE_TRACES_URL`) which injects the Better Stack source token server-side, so no
 * secret is ever shipped to the browser and the existing CSP (`connect-src 'self'`)
 * already covers it.
 *
 * Everything is gated by {@link isTelemetryEnabled}: a no-op unless we have a proxy
 * URL (prod builds default to `/ingest/traces`; other builds opt in via
 * `VITE_TRACES_URL`) AND we are not under Vitest. The Vitest guard matters because the
 * component tests run MSW with `onUnhandledRequest: 'error'` — any stray telemetry
 * request would fail them.
 */
import {
  SpanStatusCode,
  trace,
  type Attributes,
  type Span,
} from '@opentelemetry/api';
import { ZoneContextManager } from '@opentelemetry/context-zone';
import { OTLPTraceExporter } from '@opentelemetry/exporter-trace-otlp-http';
import { registerInstrumentations } from '@opentelemetry/instrumentation';
import { DocumentLoadInstrumentation } from '@opentelemetry/instrumentation-document-load';
import { FetchInstrumentation } from '@opentelemetry/instrumentation-fetch';
import {
  defaultResource,
  resourceFromAttributes,
} from '@opentelemetry/resources';
import { type SpanProcessor } from '@opentelemetry/sdk-trace-base';
import {
  BatchSpanProcessor,
  WebTracerProvider,
} from '@opentelemetry/sdk-trace-web';
import { onCLS, onFCP, onINP, onLCP, onTTFB, type Metric } from 'web-vitals';

import { API_BASE_URL } from '@/lib/api-client';

const SERVICE_NAME = 'leagueql-frontend';
const TRACER_NAME = 'leagueql-frontend';

let initialized = false;
// Set once Clerk resolves the user; attached to every span via a span processor
// (the resource is fixed at init, before the user id is known).
let currentUserId: string | undefined;

function tracesUrl(): string | undefined {
  // Explicit override — used for local-dev opt-in (set VITE_TRACES_URL in .env.local).
  const explicit = import.meta.env.VITE_TRACES_URL as string | undefined;
  if (explicit && explicit.length > 0) return explicit;
  // Production builds default to the same-origin Cloudflare proxy, so telemetry is
  // on in prod with no build-time env var required (the proxy acks 204 until the
  // Worker's OTEL_EXPORTER_TOKEN secret is set, so it's safe before that's configured).
  if (import.meta.env.PROD) return '/ingest/traces';
  return undefined;
}

/** Vitest sets this sentinel (see vite.config.ts); telemetry stays off in tests. */
function isTestEnv(): boolean {
  return import.meta.env.VITE_API_URL === 'http://test.local';
}

/** Telemetry runs only when a proxy URL is configured and we're not in tests. */
export function isTelemetryEnabled(): boolean {
  return !isTestEnv() && tracesUrl() !== undefined;
}

/** Stamps `user.id` onto every span once the signed-in user is known. */
class UserAttributeSpanProcessor implements SpanProcessor {
  onStart(span: Span): void {
    if (currentUserId) span.setAttribute('user.id', currentUserId);
  }
  onEnd(): void {
    // No-op: attribution happens on start; nothing to do when a span ends.
  }
  forceFlush(): Promise<void> {
    return Promise.resolve();
  }
  shutdown(): Promise<void> {
    return Promise.resolve();
  }
}

function escapeRegExp(value: string): string {
  return value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

function recordWebVital(metric: Metric): void {
  const span = trace
    .getTracer(TRACER_NAME)
    .startSpan(`web_vital.${metric.name}`);
  span.setAttributes({
    'web_vital.name': metric.name,
    'web_vital.value': metric.value,
    'web_vital.rating': metric.rating,
    'web_vital.id': metric.id,
  });
  span.end();
}

/**
 * Initialize tracing + Web Vitals. Safe to call unconditionally and repeatedly —
 * it returns immediately when telemetry is disabled or already initialized.
 */
export function initTelemetry(): void {
  if (initialized || !isTelemetryEnabled()) return;
  initialized = true;

  const resource = defaultResource().merge(
    resourceFromAttributes({
      'service.name': SERVICE_NAME,
      'deployment.environment': import.meta.env.PROD ? 'prod' : 'dev',
    }),
  );

  const provider = new WebTracerProvider({
    resource,
    spanProcessors: [
      new UserAttributeSpanProcessor(),
      new BatchSpanProcessor(new OTLPTraceExporter({ url: tracesUrl() })),
    ],
  });
  provider.register({ contextManager: new ZoneContextManager() });

  registerInstrumentations({
    instrumentations: [
      new DocumentLoadInstrumentation(),
      new FetchInstrumentation({
        // Inject W3C `traceparent` only on API calls so the API Lambda span
        // (BE-020) continues this trace; never leak it to third parties.
        // eslint-disable-next-line security/detect-non-literal-regexp -- input is a build-time constant and escaped via escapeRegExp.
        propagateTraceHeaderCorsUrls: [new RegExp(escapeRegExp(API_BASE_URL))],
      }),
    ],
  });

  onCLS(recordWebVital);
  onFCP(recordWebVital);
  onINP(recordWebVital);
  onLCP(recordWebVital);
  onTTFB(recordWebVital);
}

/** Associate (or clear) the signed-in user with subsequently-started spans. */
export function setTelemetryUser(userId: string | null | undefined): void {
  currentUserId = userId ?? undefined;
}

/** Emit a short span for a client-side route change (lightweight RUM). */
export function recordRouteChange(pathname: string): void {
  if (!isTelemetryEnabled()) return;
  const span = trace.getTracer(TRACER_NAME).startSpan('route_change');
  span.setAttribute('route.path', pathname);
  span.end();
}

/** Record a caught exception as an error span (used by the ErrorBoundary). */
export function recordException(error: unknown, attributes?: Attributes): void {
  if (!isTelemetryEnabled()) return;
  const span = trace
    .getTracer(TRACER_NAME)
    .startSpan('exception', { attributes });
  span.recordException(error as Error);
  span.setStatus({ code: SpanStatusCode.ERROR });
  span.end();
}
