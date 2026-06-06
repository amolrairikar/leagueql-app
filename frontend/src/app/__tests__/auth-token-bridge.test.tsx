import { render } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { AuthTokenBridge } from '../auth-token-bridge';

import { apiClient, setAuthTokenProvider } from '@/lib/api-client';

// `@clerk/react` is mocked globally (src/test/setup.ts → clerk-mock), whose
// `useAuth().getToken` resolves to 'test-token'.

function mockFetchOk() {
  vi.stubGlobal(
    'fetch',
    vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      statusText: 'OK',
      json: () => Promise.resolve({}),
    }),
  );
}

function lastInit(): RequestInit {
  const fetchMock = globalThis.fetch as ReturnType<typeof vi.fn>;
  return fetchMock.mock.calls[0][1] as RequestInit;
}

describe('AuthTokenBridge', () => {
  afterEach(() => {
    setAuthTokenProvider(null);
    vi.unstubAllGlobals();
  });

  it('registers Clerk getToken so requests carry the bearer token', async () => {
    render(<AuthTokenBridge />);
    mockFetchOk();
    await apiClient.post('/x', {});
    expect((lastInit().headers as Record<string, string>).Authorization).toBe(
      'Bearer test-token',
    );
  });

  it('clears the provider on unmount so later requests are unauthenticated', async () => {
    const { unmount } = render(<AuthTokenBridge />);
    unmount();
    mockFetchOk();
    await apiClient.post('/y', {});
    expect(
      (lastInit().headers as Record<string, string>).Authorization,
    ).toBeUndefined();
  });
});
