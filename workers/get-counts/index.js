export default {
  async fetch(request, env, ctx) {
    const origin = request.headers.get("Origin");
    const allowedOrigins = [
      "https://leagueql.com",
      "http://localhost:5173",
    ];

    const count = await env.COUNTS_KV.get("leagueCount");

    return new Response(JSON.stringify({ leagueCount: parseInt(count ?? "0") }), {
      headers: {
        "Content-Type": "application/json",
        "Access-Control-Allow-Origin": allowedOrigins.includes(origin) ? origin : allowedOrigins[0],
        "Cache-Control": "public, max-age=300",
      },
    });
  }
};