import { describe, expect, it } from 'vitest';

// Import the shipped `public/_headers` as a raw string (Vite `?raw`), so the assertions
// run against the exact bytes Cloudflare serves without needing Node fs/path types.
import headers from '../../../public/_headers?raw';

// The single CSP directive line (Report-Only until validated against the running app, then
// renamed to the enforcing `Content-Security-Policy`). FE-024.
const cspLine =
  headers
    .split('\n')
    .map((l) => l.trim())
    .find(
      (l) => !l.startsWith('#') && l.startsWith('Content-Security-Policy'),
    ) ?? '';

describe('public/_headers (FE-024 security headers)', () => {
  it('enforces the hardening response headers', () => {
    expect(headers).toContain('X-Content-Type-Options: nosniff');
    expect(headers).toContain(
      'Referrer-Policy: strict-origin-when-cross-origin',
    );
    expect(headers).toContain('Strict-Transport-Security: max-age=');
    expect(headers).toContain('X-Frame-Options: DENY');
    expect(headers).toContain('Permissions-Policy:');
  });

  it('ships a Content-Security-Policy with the locked-down baseline', () => {
    expect(cspLine).not.toBe('');
    expect(cspLine).toContain("default-src 'self'");
    expect(cspLine).toContain("frame-ancestors 'none'");
    expect(cspLine).toContain("object-src 'none'");
    expect(cspLine).toContain("base-uri 'self'");
  });

  it('allowlists the Clerk, API, and Stripe runtime origins', () => {
    // Clerk Frontend API + SDK + bot-protection script origins.
    expect(cspLine).toContain('https://clerk.leagueql.com');
    expect(cspLine).toContain('https://*.clerk.accounts.dev');
    expect(cspLine).toContain('https://challenges.cloudflare.com');
    // The API for connect-src (prod + the build-time dev token).
    expect(cspLine).toContain('https://api.leagueql.com');
    expect(cspLine).toContain('__VITE_DEV_API_URL__');
    // Stripe checkout/billing redirect targets.
    expect(cspLine).toContain('https://*.stripe.com');
  });

  it('permits inline styles and Clerk blob workers', () => {
    // Required by the dynamic inline <style> in ui/chart.tsx plus Tailwind/Clerk styles.
    expect(cspLine).toContain("style-src 'self' 'unsafe-inline'");
    // Clerk loads web workers from blob: URLs.
    expect(cspLine).toContain("worker-src 'self' blob:");
  });
});
