// ── Base URL ──────────────────────────────────────────────────────────────────
// Override at any time via VITE_API_URL (e.g. http://127.0.0.1:8000 for local).
// Without an override: production build → api.leagueql.com, dev build → AWS API GW.

function getBaseUrl(): string {
  const override = import.meta.env.VITE_API_URL as string | undefined;
  if (override) return override;
  if (import.meta.env.PROD) return 'https://api.leagueql.com';
  const devUrl = import.meta.env.VITE_DEV_API_URL as string | undefined;
  if (!devUrl)
    throw new Error(
      'VITE_DEV_API_URL must be set in development (see .env.local)',
    );
  return devUrl;
}

export const API_BASE_URL = getBaseUrl();

// ── Error type ────────────────────────────────────────────────────────────────

export class ApiError extends Error {
  readonly status: number;
  readonly statusText: string;

  constructor(status: number, statusText: string, message: string) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.statusText = statusText;
  }
}

// ── Auth token ──────────────────────────────────────────────────────────────
// The API client never reads a credential cookie itself. A provider (registered
// once at app init from Clerk's `useAuth().getToken` via `AuthTokenBridge`)
// supplies a fresh, short-lived session JWT per request, so the bearer token is
// not parsed out of the JS-readable `__session` cookie (LQL-05 / FE-019).

type AuthTokenProvider = () => Promise<string | null | undefined>;

let authTokenProvider: AuthTokenProvider | null = null;

/**
 * Register (or clear, with `null`) the async getter the client uses to obtain a
 * bearer token for each request. Called from `AuthTokenBridge` with Clerk's
 * `getToken`. Until a provider is registered, requests are sent unauthenticated.
 */
export function setAuthTokenProvider(provider: AuthTokenProvider | null): void {
  authTokenProvider = provider;
}

async function getSessionToken(): Promise<string | null> {
  if (!authTokenProvider) return null;
  try {
    return (await authTokenProvider()) ?? null;
  } catch {
    // A failure to mint a token (e.g. signed out / Clerk not loaded) sends the
    // request unauthenticated; the backend authorizer then returns 401.
    return null;
  }
}

// ── Fetch core ────────────────────────────────────────────────────────────────

// Per-request options. Errors always reject the returned promise so each caller
// (feature) surfaces them locally; there is no global error sink.
interface FetchOpts {
  skipCache?: boolean;
}

async function _doFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const token = await getSessionToken();
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...init?.headers,
    },
    ...init,
  });

  if (!response.ok) {
    let message: string;
    try {
      const body = (await response.json()) as Record<string, unknown>;
      message =
        typeof body.message === 'string'
          ? body.message
          : typeof body.detail === 'string'
            ? body.detail
            : response.statusText;
    } catch {
      message = response.statusText;
    }
    throw new ApiError(response.status, response.statusText, message);
  }

  const data: unknown = await response.json();
  return data as T;
}

// GET deduplication: in-flight requests are shared; settled responses are cached for CACHE_TTL_MS.
const CACHE_TTL_MS = 30_000;
const _inflight = new Map<string, Promise<unknown>>();
const _cache = new Map<string, { data: unknown; expires: number }>();

function apiFetch<T>(
  path: string,
  init?: RequestInit,
  opts?: FetchOpts,
): Promise<T> {
  const method = (init?.method ?? 'GET').toUpperCase();
  if (method !== 'GET') return _doFetch<T>(path, init);

  // Polling endpoints (e.g. job status) must read fresh each time, so skip both
  // the settled-response cache and in-flight dedup.
  if (opts?.skipCache) return _doFetch<T>(path, init);

  const cached = _cache.get(path);
  if (cached && Date.now() < cached.expires)
    return Promise.resolve(cached.data as T);

  const existing = _inflight.get(path);
  if (existing) return existing as Promise<T>;

  const promise = _doFetch<T>(path, init).then(
    (data) => {
      _cache.set(path, { data, expires: Date.now() + CACHE_TTL_MS });
      _inflight.delete(path);
      return data;
    },
    (err: unknown) => {
      _inflight.delete(path);
      throw err;
    },
  );
  _inflight.set(path, promise);
  return promise;
}

export function clearApiCache(): void {
  _cache.clear();
  _inflight.clear();
}

// ── Public client ─────────────────────────────────────────────────────────────

export const apiClient = {
  get<T>(
    path: string,
    init?: Omit<RequestInit, 'method'>,
    opts?: FetchOpts,
  ): Promise<T> {
    return apiFetch<T>(path, { ...init, method: 'GET' }, opts);
  },
  post<T>(
    path: string,
    body: unknown,
    init?: Omit<RequestInit, 'method' | 'body'>,
  ): Promise<T> {
    return apiFetch<T>(path, {
      ...init,
      method: 'POST',
      body: JSON.stringify(body),
    });
  },
  put<T>(
    path: string,
    body: unknown,
    init?: Omit<RequestInit, 'method' | 'body'>,
  ): Promise<T> {
    return apiFetch<T>(path, {
      ...init,
      method: 'PUT',
      body: JSON.stringify(body),
    });
  },
  patch<T>(
    path: string,
    body: unknown,
    init?: Omit<RequestInit, 'method' | 'body'>,
  ): Promise<T> {
    return apiFetch<T>(path, {
      ...init,
      method: 'PATCH',
      body: JSON.stringify(body),
    });
  },
  delete<T>(path: string, init?: Omit<RequestInit, 'method'>): Promise<T> {
    return apiFetch<T>(path, { ...init, method: 'DELETE' });
  },
};
