import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import worker from './index.js';

const URL_TRACES = 'https://leagueql.com/ingest/traces';
const UPSTREAM = 'https://up.example/v1/traces';

// Fully-configured env (token + upstream) so requests that pass validation forward.
const CONFIGURED_ENV = {
  OTEL_EXPORTER_TOKEN: 'tok',
  OTEL_TRACES_URL: UPSTREAM,
};

const VALID_OTLP = JSON.stringify({ resourceSpans: [] });

function tracesRequest({ method = 'POST', contentType = 'application/json', body = VALID_OTLP, headers = {} } = {}) {
  const h = { ...headers };
  if (contentType !== null) h['Content-Type'] = contentType;
  return new Request(URL_TRACES, { method, headers: h, body: method === 'GET' ? undefined : body });
}

let fetchMock;

beforeEach(() => {
  fetchMock = vi.fn(async () => new Response('forwarded', { status: 200 }));
  vi.stubGlobal('fetch', fetchMock);
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe('/ingest/traces proxy', () => {
  it('rejects non-POST with 405 and does not forward', async () => {
    const res = await worker.fetch(tracesRequest({ method: 'GET' }), CONFIGURED_ENV);
    expect(res.status).toBe(405);
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it('rejects a disallowed Content-Type with 415 and does not forward', async () => {
    const res = await worker.fetch(tracesRequest({ contentType: 'text/plain' }), CONFIGURED_ENV);
    expect(res.status).toBe(415);
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it('rejects an oversized declared Content-Length with 413 and does not forward', async () => {
    const res = await worker.fetch(
      tracesRequest({ headers: { 'Content-Length': String(600 * 1024) } }),
      CONFIGURED_ENV,
    );
    expect(res.status).toBe(413);
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it('rejects an oversized actual body with 413 and does not forward', async () => {
    const big = 'x'.repeat(600 * 1024);
    const res = await worker.fetch(tracesRequest({ body: big }), CONFIGURED_ENV);
    expect(res.status).toBe(413);
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it('acks with 204 (no token attached) when the worker is unconfigured', async () => {
    const res = await worker.fetch(tracesRequest(), {});
    expect(res.status).toBe(204);
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it('rejects malformed JSON with 400 and does not forward', async () => {
    const res = await worker.fetch(tracesRequest({ body: '{not json' }), CONFIGURED_ENV);
    expect(res.status).toBe(400);
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it('rejects JSON without resourceSpans with 400 and does not forward', async () => {
    const res = await worker.fetch(tracesRequest({ body: '{"foo":1}' }), CONFIGURED_ENV);
    expect(res.status).toBe(400);
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it('forwards a valid OTLP JSON export with the token attached', async () => {
    const res = await worker.fetch(tracesRequest(), CONFIGURED_ENV);
    expect(fetchMock).toHaveBeenCalledTimes(1);
    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toBe(UPSTREAM);
    expect(init.method).toBe('POST');
    expect(init.headers.Authorization).toBe('Bearer tok');
    expect(init.headers['Content-Type']).toBe('application/json');
    expect(res.status).toBe(200);
  });

  it('forwards a protobuf export without JSON validation', async () => {
    const res = await worker.fetch(
      tracesRequest({ contentType: 'application/x-protobuf', body: 'binary-otlp-bytes' }),
      CONFIGURED_ENV,
    );
    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(fetchMock.mock.calls[0][1].headers.Authorization).toBe('Bearer tok');
    expect(res.status).toBe(200);
  });
});

describe('asset routing', () => {
  it('serves non-ingest paths via the ASSETS binding', async () => {
    const assetsFetch = vi.fn(async () => new Response('spa', { status: 200 }));
    const env = { ...CONFIGURED_ENV, ASSETS: { fetch: assetsFetch } };
    const res = await worker.fetch(new Request('https://leagueql.com/dashboard'), env);
    expect(assetsFetch).toHaveBeenCalledTimes(1);
    expect(res.status).toBe(200);
    expect(fetchMock).not.toHaveBeenCalled();
  });
});
