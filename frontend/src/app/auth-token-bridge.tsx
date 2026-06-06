import { useAuth } from '@clerk/react';
import { useEffect } from 'react';

import { setAuthTokenProvider } from '@/lib/api-client';

/**
 * Bridges Clerk's session-token getter into the API client (FE-019 / LQL-05).
 *
 * Registers `useAuth().getToken` as the API client's auth token provider so each
 * request carries a fresh, short-lived Clerk JWT. This keeps the client from
 * parsing the JS-readable `__session` cookie itself — the token is obtained
 * through the SDK and the cookie is treated as opaque. Renders nothing; mounted
 * once inside `ClerkProvider`.
 */
export function AuthTokenBridge() {
  const { getToken } = useAuth();
  useEffect(() => {
    setAuthTokenProvider(() => getToken());
    return () => setAuthTokenProvider(null);
  }, [getToken]);
  return null;
}
