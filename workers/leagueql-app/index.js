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

  const token = env.OTEL_EXPORTER_TOKEN;
  const upstream = env.OTEL_TRACES_URL;
  // Not configured on this deploy: ack with 204 so the browser exporter treats the
  // export as delivered and doesn't retry-storm against a dead endpoint.
  if (!token || !upstream) {
    return new Response(null, { status: 204 });
  }

  const body = await request.arrayBuffer();
  return fetch(upstream, {
    method: 'POST',
    headers: {
      'Content-Type':
        request.headers.get('Content-Type') || 'application/json',
      Authorization: `Bearer ${token}`,
    },
    body,
  });
}
