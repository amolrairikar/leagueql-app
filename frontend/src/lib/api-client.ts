import { useSyncExternalStore } from 'react';

// ── Base URL ──────────────────────────────────────────────────────────────────
// Override at any time via VITE_API_URL (e.g. http://127.0.0.1:8000 for local).
// Without an override: production build → api.leagueql.com, dev build → AWS API GW.

function getBaseUrl(): string {
  const override = import.meta.env.VITE_API_URL as string | undefined;
  if (override) return override;
  if (import.meta.env.PROD) return 'https://api.leagueql.com';
  return 'https://p9o8piuh38.execute-api.us-east-1.amazonaws.com';
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

// ── Error store ───────────────────────────────────────────────────────────────
// Plain module-level store so components can subscribe without a context provider.

type ErrorListener = (error: ApiError | null) => void;

const _listeners = new Set<ErrorListener>();
let _currentError: ApiError | null = null;

export function _subscribeToErrors(listener: ErrorListener): () => void {
  _listeners.add(listener);
  return () => _listeners.delete(listener);
}

export function _getErrorSnapshot(): ApiError | null {
  return _currentError;
}

function _setApiError(error: ApiError | null): void {
  _currentError = error;
  for (const listener of _listeners) listener(error);
}

export function clearApiError(): void {
  _setApiError(null);
}

// ── React hook ────────────────────────────────────────────────────────────────

export function useApiError(): ApiError | null {
  return useSyncExternalStore(_subscribeToErrors, _getErrorSnapshot);
}

// ── Fetch core ────────────────────────────────────────────────────────────────

function getSessionToken(): string | null {
  const match = /(?:^|;\s*)__session=([^;]*)/.exec(document.cookie);
  return match ? decodeURIComponent(match[1]) : null;
}

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const token = getSessionToken();
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
    const error = new ApiError(response.status, response.statusText, message);
    _setApiError(error);
    throw error;
  }

  clearApiError();
  return response.json() as Promise<T>;
}

// ── Public client ─────────────────────────────────────────────────────────────

export const apiClient = {
  get<T>(path: string, init?: Omit<RequestInit, 'method'>): Promise<T> {
    return apiFetch<T>(path, { ...init, method: 'GET' });
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
