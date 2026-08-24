# security-headers Specification

## Purpose
The Cloudflare-served frontend ships a `public/_headers` file that applies a Content-Security-Policy plus hardening response headers to every asset. The CSP is the control that bounds XSS-based token theft: it limits where injected script may execute and exfiltrate. It was rolled out in Report-Only, validated against the running app with no violations, and is now enforced.

## Requirements

### Requirement: Ship hardening response headers
`public/_headers` SHALL set `X-Content-Type-Options: nosniff`, `Referrer-Policy: strict-origin-when-cross-origin`, `Strict-Transport-Security`, `X-Frame-Options: DENY`, and a `Permissions-Policy` on all assets.

#### Scenario: Hardening headers present
- **WHEN** any asset is served
- **THEN** it carries `X-Content-Type-Options: nosniff`, `Referrer-Policy: strict-origin-when-cross-origin`, `Strict-Transport-Security`, `X-Frame-Options: DENY`, and a `Permissions-Policy` (all enforced)

### Requirement: Enforce a strict CSP with the runtime allowlist
An enforcing `Content-Security-Policy` SHALL be present with `default-src 'self'`, `frame-ancestors 'none'`, `object-src 'none'`, `base-uri 'self'`, the Clerk/API allowlist, `style-src 'unsafe-inline'`, and `worker-src blob:`.

#### Scenario: CSP present and enforcing
- **WHEN** the app loads
- **THEN** the enforcing CSP includes `default-src 'self'`, `frame-ancestors 'none'`, `object-src 'none'`, `base-uri 'self'`, the Clerk + API `connect-src` allowlist, `style-src 'unsafe-inline'` (for dynamic chart/Tailwind/Clerk styles), and `worker-src blob:` (Clerk web workers), with no violations

### Requirement: Template the dev API origin at build time
The dev API origin SHALL be templated via `__VITE_DEV_API_URL__` and substituted from `VITE_DEV_API_URL` at build time, removed when unset.

#### Scenario: Dev origin substitution
- **WHEN** the frontend is built
- **THEN** the `__VITE_DEV_API_URL__` token in `dist/_headers` is replaced with `VITE_DEV_API_URL`, or removed when unset so only the production origins remain
