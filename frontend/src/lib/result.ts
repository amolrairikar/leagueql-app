import { ApiError } from '@/lib/api-client';

/**
 * Discriminated result type for data-loading promises consumed via Suspense.
 * A success carries `data`; a failure carries a human-readable `error` message.
 */
export type Result<T> = { ok: true; data: T } | { ok: false; error: string };

/**
 * Picks the message to show for a failed data load.
 *
 * Backend detail is only surfaced for *actionable* client errors (4xx) — a 5xx
 * is server boilerplate ("Internal Server Error") and a non-`ApiError` is opaque
 * (e.g. a network "Failed to fetch"), so both fall back to the caller's own
 * feature-specific `fallbackMessage`.
 */
function errorMessage(err: unknown, fallbackMessage: string): string {
  if (err instanceof ApiError && err.status >= 400 && err.status < 500) {
    return err.message;
  }
  return fallbackMessage;
}

/**
 * Wraps a data promise into a never-rejecting `Promise<Result<T>>`.
 *
 * On success the resolved value becomes `{ ok: true, data }`; on rejection the
 * error becomes `{ ok: false, error }` (see {@link errorMessage} for which
 * message is chosen). Lets components `use()` the promise without a try/catch.
 */
export function toResult<T>(
  promise: Promise<T>,
  fallbackMessage: string,
): Promise<Result<T>> {
  return promise
    .then((data) => ({ ok: true as const, data }))
    .catch((err: unknown) => ({
      ok: false as const,
      error: errorMessage(err, fallbackMessage),
    }));
}
