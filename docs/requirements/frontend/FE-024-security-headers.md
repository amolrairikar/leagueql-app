# FE-024: Security Response Headers & Content-Security-Policy

## Description
The Cloudflare-served frontend ships a `public/_headers` file that applies a
Content-Security-Policy (CSP) plus a set of hardening response headers to every asset. The
CSP is the control that actually bounds XSS-based token theft: even though the API client no
longer parses the `__session` cookie ([FE-019](FE-019-authentication.md)), an XSS attacker
could still mint a Clerk token via the SDK while the page is open — a strict CSP is what
limits where injected script may execute and exfiltrate (closes the
[LQL-04](../../../SECURITY_FINDINGS.md) residual; addresses LQL-07).

The CSP was rolled out in `Content-Security-Policy-Report-Only` first, validated against the
running app (Clerk incl. Google sign-in, the API, charts) with no
violations, and is now shipped as the enforcing **`Content-Security-Policy`** header. The
hardening headers are likewise enforced. To debug a future policy change, the header name can
be temporarily reverted to `-Report-Only`.

## Scope
- Header source: `frontend/public/_headers` (copied verbatim by Vite to `dist/_headers`;
  honored by Cloudflare Pages / Workers Static Assets).
- Dev API origin substitution: a Vite build plugin (`vite.config.ts`) replaces the
  `__VITE_DEV_API_URL__` token in `dist/_headers` with the value of `VITE_DEV_API_URL` at
  build time, so the dev/preview API Gateway origin is not hardcoded. When the var is unset
  (e.g. production builds), the token is removed and only the production origins remain.
- The file lists **both** production and dev/preview Clerk origins in one policy so a single
  static file works for prod and preview deploys.

### Allowlisted runtime origins
- **Self** — Vite emits module scripts from `/assets/*.js` (`script-src 'self'`).
- **Clerk** — Frontend API hosts (`clerk.leagueql.com` prod, `*.clerk.accounts.dev` dev),
  `*.clerk.com`, `challenges.cloudflare.com` (bot/Turnstile), `clerk-telemetry.com`,
  `img.clerk.com`, and `worker-src blob:` (Clerk web workers).
- **API** — `https://api.leagueql.com` (prod) and `__VITE_DEV_API_URL__` (dev) in
  `connect-src`.
- **Buy Me A Coffee** — `cdn.buymeacoffee.com` in `img-src`, the origin of the donate button
  image rendered in the About dialog (`features/about/about-dialog.tsx`). The link target
  (`www.buymeacoffee.com`) is a top-level navigation and not CSP-governed.

## Edge Cases
- **Inline chart styles:** `components/ui/chart.tsx` injects a dynamic inline `<style>` and
  Tailwind/Clerk also emit inline styles, so `style-src` must include `'unsafe-inline'`.
- **JSON-LD block:** `index.html` contains an inline `application/ld+json` block. It is
  non-executable data and normally exempt from `script-src`; if Report-Only flags it, add a
  hash or move it out rather than loosening `script-src`.
- **Clerk workers:** Clerk loads web workers from `blob:` URLs, requiring `worker-src blob:`.
- **Dev vs. prod:** a single static file lists both Clerk hosts; the dev API origin is the
  only build-time-templated value. An unset `VITE_DEV_API_URL` cleanly drops the dev origin.

## Acceptance Criteria
- [x] `public/_headers` sets `X-Content-Type-Options: nosniff`,
      `Referrer-Policy: strict-origin-when-cross-origin`, `Strict-Transport-Security`,
      `X-Frame-Options: DENY`, and a `Permissions-Policy` on all assets (enforced).
- [x] An enforcing `Content-Security-Policy` is present with `default-src 'self'`,
      `frame-ancestors 'none'`, `object-src 'none'`, `base-uri 'self'`, the Clerk/API allowlist,
      `style-src 'unsafe-inline'`, and `worker-src blob:`.
- [x] The dev API origin is templated via `__VITE_DEV_API_URL__` and substituted at build time
      from `VITE_DEV_API_URL` (removed when unset).
- [x] The CSP was validated against the running app in Report-Only (no violations) before being
      switched to the enforcing header.

## Sources
`frontend/public/_headers`, `frontend/vite.config.ts`, `frontend/src/app/clerk-with-theme.tsx`,
`frontend/src/lib/api-client.ts`, `frontend/src/components/ui/chart.tsx`.
