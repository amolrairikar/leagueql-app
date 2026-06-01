/**
 * Discriminated result type for data-loading promises consumed via Suspense.
 * A success carries `data`; a failure carries a human-readable `error` message.
 */
export type Result<T> = { ok: true; data: T } | { ok: false; error: string };

/**
 * Wraps a data promise into a never-rejecting `Promise<Result<T>>`.
 *
 * On success the resolved value becomes `{ ok: true, data }`; on rejection the
 * error message (or `fallbackMessage` for non-Error throwables) becomes
 * `{ ok: false, error }`. Lets components `use()` the promise without a try/catch.
 */
export function toResult<T>(
  promise: Promise<T>,
  fallbackMessage: string,
): Promise<Result<T>> {
  return promise
    .then((data) => ({ ok: true as const, data }))
    .catch((err: unknown) => ({
      ok: false as const,
      error: err instanceof Error ? err.message : fallbackMessage,
    }));
}
