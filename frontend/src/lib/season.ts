import { type Result, toResult } from '@/lib/result';

/**
 * The most recent season (highest numeric value) from a league's season list,
 * or `''` when the list is empty. Used to seed the default selected season on
 * every season-scoped feature page.
 */
export function latestSeason(seasons: readonly string[]): string {
  return [...seasons].sort((a, b) => Number(b) - Number(a))[0] ?? '';
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
