import { afterEach, describe, expect, it, vi } from 'vitest';

import { createBillingPortalSession, createCheckoutSession } from '../billing';

function mockFetchOk(body: unknown) {
  const fetchMock = vi.fn().mockResolvedValue({
    ok: true,
    status: 200,
    statusText: 'OK',
    json: () => Promise.resolve(body),
  });
  vi.stubGlobal('fetch', fetchMock);
  return fetchMock;
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe('billing api', () => {
  it('createCheckoutSession POSTs to the checkout endpoint with platform and plan', async () => {
    const fetchMock = mockFetchOk({ detail: 'ok', data: { url: 'https://c' } });

    const res = await createCheckoutSession('123', 'SLEEPER', 'YEARLY');

    expect(res.data.url).toBe('https://c');
    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toContain('/leagues/123/checkout-session');
    expect(url).toContain('platform=SLEEPER');
    expect(url).toContain('plan=YEARLY');
    expect(url).not.toContain('returnPath');
    expect(init.method).toBe('POST');
  });

  it('createCheckoutSession includes the returnPath when provided', async () => {
    const fetchMock = mockFetchOk({ detail: 'ok', data: { url: 'https://c' } });

    await createCheckoutSession(
      '123',
      'SLEEPER',
      'MONTHLY',
      '/schedule-swap?x=1',
    );

    const [url] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toContain(
      `returnPath=${encodeURIComponent('/schedule-swap?x=1')}`,
    );
  });

  it('createBillingPortalSession POSTs to the portal endpoint', async () => {
    const fetchMock = mockFetchOk({ detail: 'ok', data: { url: 'https://p' } });

    const res = await createBillingPortalSession();

    expect(res.data.url).toBe('https://p');
    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toContain('/billing-portal-session');
    expect(init.method).toBe('POST');
  });
});
