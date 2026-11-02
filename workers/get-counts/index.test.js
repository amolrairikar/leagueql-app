import { describe, expect, it, vi } from 'vitest';

import worker from './index.js';

const URL = 'https://api.leagueql.com/counts';

function env(value) {
  return { COUNTS_KV: { get: vi.fn(async () => value) } };
}

function get(origin) {
  return new Request(URL, { headers: origin ? { Origin: origin } : {} });
}

describe('GET /counts', () => {
  it('returns the KV league count as JSON', async () => {
    const res = await worker.fetch(get('https://leagueql.com'), env('42'));
    expect(res.status).toBe(200);
    expect(res.headers.get('Content-Type')).toBe('application/json');
    expect(await res.json()).toEqual({ leagueCount: 42 });
  });

  it('reads the leagueCount key', async () => {
    const e = env('1');
    await worker.fetch(get(), e);
    expect(e.COUNTS_KV.get).toHaveBeenCalledWith('leagueCount');
  });

  it('defaults to 0 when the key has never been synced', async () => {
    const res = await worker.fetch(get(), env(null));
    expect(await res.json()).toEqual({ leagueCount: 0 });
  });

  it('is edge-cacheable for 5 minutes and varies on Origin', async () => {
    const res = await worker.fetch(get(), env('1'));
    expect(res.headers.get('Cache-Control')).toBe('public, max-age=300');
    expect(res.headers.get('Vary')).toBe('Origin');
  });
});

describe('CORS origin handling', () => {
  it.each(['https://leagueql.com', 'http://localhost:5173'])(
    'echoes the allowed origin %s',
    async (origin) => {
      const res = await worker.fetch(get(origin), env('1'));
      expect(res.headers.get('Access-Control-Allow-Origin')).toBe(origin);
    },
  );

  it.each([['https://evil.example'], [null]])(
    'falls back to the production origin for %s',
    async (origin) => {
      const res = await worker.fetch(get(origin), env('1'));
      expect(res.headers.get('Access-Control-Allow-Origin')).toBe(
        'https://leagueql.com',
      );
    },
  );
});

describe('OPTIONS preflight', () => {
  const preflight = (origin) =>
    new Request(URL, {
      method: 'OPTIONS',
      headers: origin ? { Origin: origin } : {},
    });

  it('answers 204 without touching KV', async () => {
    const e = env('1');
    const res = await worker.fetch(preflight('https://leagueql.com'), e);
    expect(res.status).toBe(204);
    expect(e.COUNTS_KV.get).not.toHaveBeenCalled();
  });

  it('allows the OTel trace-context headers the browser SDK injects', async () => {
    const res = await worker.fetch(preflight('https://leagueql.com'), env('1'));
    const allowed = res.headers.get('Access-Control-Allow-Headers');
    expect(allowed).toContain('traceparent');
    expect(allowed).toContain('tracestate');
    expect(allowed).toContain('Content-Type');
  });

  it('advertises GET/OPTIONS and is never cached', async () => {
    const res = await worker.fetch(preflight('https://leagueql.com'), env('1'));
    expect(res.headers.get('Access-Control-Allow-Methods')).toBe('GET, OPTIONS');
    expect(res.headers.get('Access-Control-Max-Age')).toBe('3600');
    expect(res.headers.get('Cache-Control')).toBe('no-store');
    expect(res.headers.get('Vary')).toBe('Origin');
  });

  it('echoes an allowed origin and rejects unknown ones', async () => {
    const ok = await worker.fetch(preflight('http://localhost:5173'), env('1'));
    expect(ok.headers.get('Access-Control-Allow-Origin')).toBe(
      'http://localhost:5173',
    );
    const bad = await worker.fetch(preflight('https://evil.example'), env('1'));
    expect(bad.headers.get('Access-Control-Allow-Origin')).toBe(
      'https://leagueql.com',
    );
  });
});
