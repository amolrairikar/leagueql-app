/**
 * Cloudflare Worker entry for the LeagueQL frontend (FE-029).
 *
 * Serves the static SPA via the `ASSETS` binding and adds a same-origin
 * `POST /ingest/traces` proxy that injects the Axiom ingest token + dataset
 * server-side and forwards OTLP trace data to Axiom. This keeps the Axiom secret
 * out of the browser bundle entirely; the browser exporter only ever talks to its
 * own origin (so the CSP `connect-src 'self'` already covers it — FE-024).
 *
 * Per-deploy Cloudflare config (set separately on the dev and prod deploys):
 *   - AXIOM_API_TOKEN  (secret) — Axiom ingest token (`wrangler secret put ...`)
 *   - AXIOM_DATASET    (var)    — `leagueql-dev` | `leagueql-prod`
 *   - AXIOM_TRACES_URL (var, optional) — defaults to https://api.axiom.co/v1/traces
 */
const DEFAULT_AXIOM_TRACES_URL = 'https://api.axiom.co/v1/traces';

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

  const token = env.AXIOM_API_TOKEN;
  const dataset = env.AXIOM_DATASET;
  // Not configured on this deploy: ack with 204 so the browser exporter treats the
  // export as delivered and doesn't retry-storm against a dead endpoint.
  if (!token || !dataset) {
    return new Response(null, { status: 204 });
  }

  const upstream = env.AXIOM_TRACES_URL || DEFAULT_AXIOM_TRACES_URL;
  const body = await request.arrayBuffer();
  return fetch(upstream, {
    method: 'POST',
    headers: {
      'Content-Type':
        request.headers.get('Content-Type') || 'application/json',
      Authorization: `Bearer ${token}`,
      'X-Axiom-Dataset': dataset,
    },
    body,
  });
}
