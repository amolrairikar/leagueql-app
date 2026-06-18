import { afterEach, describe, expect, it, vi } from 'vitest';

import { ApiError, apiClient, setAuthTokenProvider } from '../api-client';

// ── Helpers ───────────────────────────────────────────────────────────────────

function mockFetchOk(body: unknown) {
  vi.stubGlobal(
    'fetch',
    vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      statusText: 'OK',
      json: () => Promise.resolve(body),
    }),
  );
}

function mockFetchError(status: number, body?: unknown) {
  vi.stubGlobal(
    'fetch',
    vi.fn().mockResolvedValue({
      ok: false,
      status,
      statusText: `Error ${status}`,
      json:
        body !== undefined
          ? () => Promise.resolve(body)
          : () => Promise.reject(new Error('no json')),
    }),
  );
}

function fetchMock() {
  return globalThis.fetch as ReturnType<typeof vi.fn>;
}

// ── ApiError ──────────────────────────────────────────────────────────────────

describe('ApiError', () => {
  it('sets name, status, statusText, and message', () => {
    const err = new ApiError(404, 'Not Found', 'Resource not found');
    expect(err.name).toBe('ApiError');
    expect(err.status).toBe(404);
    expect(err.statusText).toBe('Not Found');
    expect(err.message).toBe('Resource not found');
    expect(err).toBeInstanceOf(Error);
  });
});

// ── Failed requests ─────────────────────────────────────────────────────────

describe('failed requests', () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('rejects with an ApiError carrying the response status', async () => {
    mockFetchError(500);
    await expect(apiClient.post('/fail', {})).rejects.toThrow(ApiError);
    await expect(apiClient.post('/fail', {})).rejects.toMatchObject({
      status: 500,
    });
  });
});

// ── Session token ─────────────────────────────────────────────────────────────

describe('session token', () => {
  afterEach(() => {
    setAuthTokenProvider(null);
    vi.unstubAllGlobals();
  });

  it('includes Authorization header from the registered token provider', async () => {
    setAuthTokenProvider(() => Promise.resolve('mytoken123'));
    mockFetchOk({});
    await apiClient.post('/auth-set', {});
    const [, init] = fetchMock().mock.calls[0] as [string, RequestInit];
    expect((init.headers as Record<string, string>).Authorization).toBe(
      'Bearer mytoken123',
    );
  });

  it('omits Authorization header when no token provider is registered', async () => {
    setAuthTokenProvider(null);
    mockFetchOk({});
    await apiClient.post('/auth-absent', {});
    const [, init] = fetchMock().mock.calls[0] as [string, RequestInit];
    expect(
      (init.headers as Record<string, string>).Authorization,
    ).toBeUndefined();
  });

  it('omits Authorization header when the provider yields no token', async () => {
    setAuthTokenProvider(() => Promise.resolve(null));
    mockFetchOk({});
    await apiClient.post('/auth-null', {});
    const [, init] = fetchMock().mock.calls[0] as [string, RequestInit];
    expect(
      (init.headers as Record<string, string>).Authorization,
    ).toBeUndefined();
  });

  it('omits Authorization header when the provider throws', async () => {
    setAuthTokenProvider(() => Promise.reject(new Error('no session')));
    mockFetchOk({});
    await apiClient.post('/auth-throws', {});
    const [, init] = fetchMock().mock.calls[0] as [string, RequestInit];
    expect(
      (init.headers as Record<string, string>).Authorization,
    ).toBeUndefined();
  });
});

// ── Error response parsing ────────────────────────────────────────────────────

describe('error response parsing', () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('uses body.message when present', async () => {
    mockFetchError(422, { message: 'Validation failed' });
    await expect(apiClient.post('/parse-message', {})).rejects.toMatchObject({
      message: 'Validation failed',
      status: 422,
    });
  });

  it('uses body.detail when message is absent', async () => {
    mockFetchError(422, { detail: 'Field required' });
    await expect(apiClient.post('/parse-detail', {})).rejects.toMatchObject({
      message: 'Field required',
    });
  });

  it('falls back to statusText when response body is not JSON', async () => {
    mockFetchError(503);
    await expect(
      apiClient.post('/parse-status-text', {}),
    ).rejects.toMatchObject({
      message: 'Error 503',
    });
  });
});

// ── GET caching and deduplication ─────────────────────────────────────────────

describe('GET caching', () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    vi.useRealTimers();
  });

  it('serves cached result on second GET within TTL', async () => {
    mockFetchOk({ val: 'cached' });
    const r1 = await apiClient.get<{ val: string }>('/cache-hit-1');
    const r2 = await apiClient.get<{ val: string }>('/cache-hit-1');
    expect(fetchMock().mock.calls).toHaveLength(1);
    expect(r1).toEqual({ val: 'cached' });
    expect(r2).toEqual({ val: 'cached' });
  });

  it('re-fetches after TTL (30 s) expires', async () => {
    vi.useFakeTimers();
    mockFetchOk({ val: 'fresh' });
    await apiClient.get('/cache-ttl-1');
    vi.advanceTimersByTime(31_000);
    await apiClient.get('/cache-ttl-1');
    expect(fetchMock().mock.calls).toHaveLength(2);
  });

  it('honors a per-call cacheTtlMs override past the default TTL', async () => {
    vi.useFakeTimers();
    mockFetchOk({ val: 'long' });
    const opts = { cacheTtlMs: 5 * 60 * 1000 };
    await apiClient.get('/cache-ttl-custom', undefined, opts);
    // Past the 30 s default but within the 5 min override → still cached.
    vi.advanceTimersByTime(60_000);
    await apiClient.get('/cache-ttl-custom', undefined, opts);
    expect(fetchMock().mock.calls).toHaveLength(1);
    // Past the override → re-fetches.
    vi.advanceTimersByTime(5 * 60 * 1000);
    await apiClient.get('/cache-ttl-custom', undefined, opts);
    expect(fetchMock().mock.calls).toHaveLength(2);
  });

  it('deduplicates concurrent GET requests to the same path', async () => {
    let resolveFetch!: () => void;
    const barrier = new Promise<void>((res) => {
      resolveFetch = res;
    });

    vi.stubGlobal(
      'fetch',
      vi.fn().mockReturnValue(
        barrier.then(() => ({
          ok: true,
          status: 200,
          statusText: 'OK',
          json: () => Promise.resolve({ val: 'deduped' }),
        })),
      ),
    );

    const p1 = apiClient.get<{ val: string }>('/dedup-1');
    const p2 = apiClient.get<{ val: string }>('/dedup-1');

    // Let the async token lookup settle so the single underlying fetch is
    // dispatched (the two GETs are deduped onto one in-flight request), then
    // assert fetch ran exactly once before either resolves.
    await new Promise((resolve) => setTimeout(resolve, 0));
    expect(fetchMock().mock.calls).toHaveLength(1);

    resolveFetch();
    const [r1, r2] = await Promise.all([p1, p2]);
    expect(r1).toEqual({ val: 'deduped' });
    expect(r2).toEqual({ val: 'deduped' });
    expect(fetchMock().mock.calls).toHaveLength(1);
  });
});

// ── Non-GET methods ───────────────────────────────────────────────────────────

describe('non-GET methods', () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('POST sends method=POST with JSON-serialised body', async () => {
    mockFetchOk({});
    await apiClient.post('/method-post', { key: 'value' });
    const [, init] = fetchMock().mock.calls[0] as [string, RequestInit];
    expect(init.method).toBe('POST');
    expect(init.body).toBe('{"key":"value"}');
  });

  it('PUT sends method=PUT with JSON-serialised body', async () => {
    mockFetchOk({});
    await apiClient.put('/method-put', { key: 'value' });
    const [, init] = fetchMock().mock.calls[0] as [string, RequestInit];
    expect(init.method).toBe('PUT');
    expect(init.body).toBe('{"key":"value"}');
  });

  it('PATCH sends method=PATCH with JSON-serialised body', async () => {
    mockFetchOk({});
    await apiClient.patch('/method-patch', { x: 1 });
    const [, init] = fetchMock().mock.calls[0] as [string, RequestInit];
    expect(init.method).toBe('PATCH');
    expect(init.body).toBe('{"x":1}');
  });

  it('DELETE sends method=DELETE', async () => {
    mockFetchOk({});
    await apiClient.delete('/method-delete');
    const [, init] = fetchMock().mock.calls[0] as [string, RequestInit];
    expect(init.method).toBe('DELETE');
  });

  it('POST bypasses the GET cache and calls fetch each time', async () => {
    mockFetchOk({ ok: true });
    await apiClient.post('/no-cache-post', {});
    await apiClient.post('/no-cache-post', {});
    expect(fetchMock().mock.calls).toHaveLength(2);
  });
});
