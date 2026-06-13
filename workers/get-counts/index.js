const ALLOWED_ORIGINS = ["https://leagueql.com", "http://localhost:5173"];

// `traceparent`/`tracestate` must be allowed because the browser OTel SDK (FE-029)
// injects W3C trace context on every API-origin call, which turns the landing-page
// fetch (BE-013) into a CORS-preflighted request.
const ALLOWED_HEADERS = "Content-Type, traceparent, tracestate";

function corsOrigin(request) {
  const origin = request.headers.get("Origin");
  return ALLOWED_ORIGINS.includes(origin) ? origin : ALLOWED_ORIGINS[0];
}

export default {
  async fetch(request, env, ctx) {
    const allowOrigin = corsOrigin(request);

    // CORS preflight: answer before touching KV, and never let this response be
    // edge-cached as the GET body (which lacks Access-Control-Allow-Headers).
    if (request.method === "OPTIONS") {
      return new Response(null, {
        status: 204,
        headers: {
          "Access-Control-Allow-Origin": allowOrigin,
          "Access-Control-Allow-Methods": "GET, OPTIONS",
          "Access-Control-Allow-Headers": ALLOWED_HEADERS,
          "Access-Control-Max-Age": "3600",
          "Cache-Control": "no-store",
          Vary: "Origin",
        },
      });
    }

    const count = await env.COUNTS_KV.get("leagueCount");

    return new Response(JSON.stringify({ leagueCount: parseInt(count ?? "0") }), {
      headers: {
        "Content-Type": "application/json",
        "Access-Control-Allow-Origin": allowOrigin,
        "Cache-Control": "public, max-age=300",
        Vary: "Origin",
      },
    });
  },
};
