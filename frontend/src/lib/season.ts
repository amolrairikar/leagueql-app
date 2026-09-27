import { type Result, toResult } from '@/lib/result';

/** Sleeper's NFL-state endpoint, the source of truth for the current season. */
const SLEEPER_NFL_STATE_URL = 'https://api.sleeper.app/v1/state/nfl';

/**
 * The most recent season (highest numeric value) from a league's season list,
 * or `''` when the list is empty. Used to seed the default selected season on
 * every season-scoped feature page.
 */
export function latestSeason(seasons: readonly string[]): string {
  return [...seasons].sort((a, b) => Number(b) - Number(a))[0] ?? '';
}

/**
 * The current fantasy season (NFL season year) derived from `now`. The NFL
 * season flips in September, so before September the current fantasy season is
 * still the prior calendar year — this mirrors the backend's current-season
 * gate (`nfl_state["season"]`). Used as the offline fallback for
 * {@link getCurrentNflSeason} and by the Sleeper stale-season banner.
 */
export function currentFantasySeason(now: Date): number {
  const year = now.getFullYear();
  return now.getMonth() >= 8 ? year : year - 1;
}

/**
 * The current NFL season as a 4-digit string, fetched from Sleeper's NFL-state
 * endpoint so ESPN onboards/refreshes never have to ask the user for it.
 *
 * Fails open: on any error (non-OK response, network failure, or an unparseable
 * / missing `season`) it falls back to the clock-derived
 * {@link currentFantasySeason}, so onboarding is never blocked by Sleeper
 * availability. Never throws. Mirrors the direct-Sleeper-fetch precedent in
 * `features/migrate_league/api-calls.ts` (raw `fetch`, no auth header).
 */
export async function getCurrentNflSeason(): Promise<string> {
  try {
    const res = await fetch(SLEEPER_NFL_STATE_URL);
    if (!res.ok) throw new Error(`Sleeper NFL state responded ${res.status}`);
    const state = (await res.json()) as { season?: unknown };
    if (typeof state.season === 'string' && /^\d{4}$/.test(state.season)) {
      return state.season;
    }
    throw new Error('Sleeper NFL state missing a valid season');
  } catch {
    return String(currentFantasySeason(new Date()));
  }
}

/**
 * Builds the never-rejecting `Result` promise for a season-scoped list query,
 * consumed by a Suspense boundary via `use()`.
 *
 * When `ready` is false (no league id / no season selected yet) it resolves to
 * an empty success so the consumer renders its empty state rather than loading
 * forever; otherwise it wraps `fetch()` with {@link toResult}. Centralizes the
 * guard + empty-fallback + `toResult` boilerplate repeated across features — the
 * caller keeps its own `useMemo` so the dependency array stays local and
 * lint-checkable.
 */
export function seasonQuery<T>(
  ready: boolean,
  fetch: () => Promise<{ data: T[] }>,
  errorMessage: string,
): Promise<Result<T[]>> {
  return ready
    ? toResult(
        fetch().then((r) => r.data),
        errorMessage,
      )
    : Promise.resolve({ ok: true as const, data: [] as T[] });
}
