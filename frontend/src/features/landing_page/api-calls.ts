// `/counts` is served by a Cloudflare Worker (workers/get-counts) on the production API
// host, not by API Gateway, so it is not reachable through `API_BASE_URL` (which points at
// API Gateway in dev builds). Always read the public production endpoint.
const COUNTS_URL = 'https://api.leagueql.com/counts';

/** Total onboarded leagues for the landing-page social proof, or null on any failure. */
export async function getLeagueCount(): Promise<number | null> {
  try {
    const response = await fetch(COUNTS_URL);
    const data = (await response.json()) as { leagueCount: number };
    return data.leagueCount;
  } catch {
    return null;
  }
}
