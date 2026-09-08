/**
 * Cloudflare Worker entry for the LeagueQL frontend (frontend/observability).
 *
 * Serves the static SPA via the `ASSETS` binding and adds a same-origin
 * `POST /ingest/traces` proxy that injects the Better Stack OTLP source token
 * server-side and forwards OTLP trace data to Better Stack. This keeps the token
 * out of the browser bundle entirely; the browser exporter only ever talks to its
 * own origin (so the CSP `connect-src 'self'` already covers it — frontend/security-headers).
 *
 * Per-deploy Cloudflare config (set separately on the dev and prod deploys):
 *   - OTEL_EXPORTER_TOKEN (secret) — Better Stack source token (`wrangler secret put ...`)
 *   - OTEL_TRACES_URL     (var)    — the source's OTLP traces URL
 *                                    (https://<ingesting-host>/v1/traces)
 */

// The endpoint is intentionally unauthenticated — anonymous landing-page telemetry
// is expected, and open Clerk sign-up would make auth an ineffective abuse control.
// Instead we bound and validate each request BEFORE attaching the source token, so
// the proxy can't be used to exhaust the Better Stack ingest quota or inject
// arbitrary non-OTLP data (see SECURITY_AUDIT SEC-02 / frontend/observability).
const MAX_TRACE_BODY_BYTES = 512 * 1024; // ~500 KB — comfortably above a normal OTLP batch
const ALLOWED_CONTENT_TYPES = ['application/x-protobuf', 'application/json'];

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    if (url.pathname === '/ingest/traces') {
      return handleTraces(request, env);
    }
    // Everything else is a static asset / SPA route.
    return env.ASSETS.fetch(request);
  },
};

async function handleTraces(request, env) {
  if (request.method !== 'POST') {
    return new Response('Method Not Allowed', { status: 405 });
  }

  // Reject anything that isn't an OTLP export before touching the token.
  const contentType = (request.headers.get('Content-Type') || '')
    .split(';')[0]
    .trim()
    .toLowerCase();
  if (!ALLOWED_CONTENT_TYPES.includes(contentType)) {
    return new Response('Unsupported Media Type', { status: 415 });
  }

  // Reject oversized bodies before forwarding so one request can't ship huge volume.
  // Check the declared length first (cheap), then the actual read length in case
  // Content-Length is absent or understated.
  const declaredLength = Number(request.headers.get('Content-Length'));
  if (Number.isFinite(declaredLength) && declaredLength > MAX_TRACE_BODY_BYTES) {
    return new Response('Payload Too Large', { status: 413 });
  }

  const token = env.OTEL_EXPORTER_TOKEN;
  const upstream = env.OTEL_TRACES_URL;
  // Not configured on this deploy: ack with 204 so the browser exporter treats the
  // export as delivered and doesn't retry-storm against a dead endpoint.
  if (!token || !upstream) {
    return new Response(null, { status: 204 });
  }

  const body = await request.arrayBuffer();
  if (body.byteLength > MAX_TRACE_BODY_BYTES) {
    return new Response('Payload Too Large', { status: 413 });
  }

  // Lightweight structural sanity check: a JSON OTLP trace export is an object
  // with a top-level `resourceSpans`. Reject obviously-malformed JSON before
  // forwarding. Protobuf bodies are opaque here, so they pass through on the
  // content-type + size checks alone.
  if (contentType === 'application/json') {
    try {
      const parsed = JSON.parse(new TextDecoder().decode(body));
      if (!parsed || typeof parsed !== 'object' || !('resourceSpans' in parsed)) {
        return new Response('Bad Request', { status: 400 });
      }
    } catch {
      return new Response('Bad Request', { status: 400 });
    }
  }

  return fetch(upstream, {
    method: 'POST',
    headers: {
      'Content-Type': contentType,
      Authorization: `Bearer ${token}`,
    },
    body,
  });
}
