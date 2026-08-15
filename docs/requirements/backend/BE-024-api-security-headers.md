# BE-024: API Security Response Headers & Cache-Control Policy

## Description
The API Lambda (FastAPI behind API Gateway → Mangum) stamps a set of hardening **security
response headers** on **every** response via a single `@app.middleware("http")` in
`src/api/main.py`, and applies a **default-deny `Cache-Control` policy** so authenticated /
private responses are never cacheable unless a route deliberately opts in.

This is the API-origin counterpart to [FE-024](../frontend/FE-024-security-headers.md), which
hardens the Cloudflare-served frontend via a static `public/_headers` file. The API is a
**separate origin** (`api.leagueql.com`) that Cloudflare's `_headers` never touches, so it
carries its own headers set in application code.

The API is **JSON-only** (no HTML rendering) and is reached cross-origin via `fetch` from the
SPA, so most classic document-oriented headers are **defense-in-depth** rather than primary
controls — they bound the edge case where a browser is tricked into treating an API response as
a document. The headers are applied by application middleware, **not** the OpenAPI contract or
API Gateway, so they cover every route (including error responses) uniformly.

### Headers set (all responses)
- **`X-Content-Type-Options: nosniff`** — stops a browser MIME-sniffing a JSON body (which may
  echo attacker-influenced third-party data — ESPN member names, error `detail` strings) into an
  executable HTML/JS document. Highest-value header here.
- **`Content-Security-Policy: default-src 'none'; frame-ancestors 'none'; base-uri 'none'`** —
  a containment policy: if a response is ever rendered as a document (a cold-start/error HTML
  body, a gateway response), nothing in it may load or execute, and it cannot be framed. Tight
  `'none'` is correct for a pure-JSON API — do **not** copy the frontend's permissive CSP here.
- **`Strict-Transport-Security: max-age=63072000; includeSubDomains`** — pins HTTPS in the
  browser so the `Authorization: Bearer <Clerk JWT>` on every API call never rides a plaintext
  request that an active MITM (hostile Wi-Fi, SSL-stripping proxy) could intercept. API Gateway
  is already HTTPS-only; the value is entirely browser-side, on the request before it reaches us.
- **`X-Frame-Options: DENY`** — legacy clickjacking cover for older browsers that ignore CSP
  `frame-ancestors`; redundant-but-harmless belt-and-suspenders.

Headers deliberately **omitted** as near-zero value for a JSON API: `Referrer-Policy` and
`Permissions-Policy` (govern rendered documents/frames, not `fetch`ed JSON) and the deprecated
`X-XSS-Protection`.

### Cache-Control audit outcome (default-deny)
The middleware sets `Cache-Control: no-store` **only when the handler did not set its own**
(`setdefault`), so route-level intent wins. The audit of every route:

| Route | Cache-Control | Rationale |
|-------|---------------|-----------|
| `GET /leagues/{id}/query` | `private, max-age=300` (route-set) | Per-member data; browser-only cache is an intentional opt-in for read performance. |
| `GET /feature-flags`, `GET /leagues/{id}`, `GET /jobs/{id}` | `no-store` (route-set, kept explicit for intent) | Per-user / transient data. |
| `POST /leagues/{id}/transfer-token` | `no-store` (middleware default) | **Returns a plaintext secret token** — the key motivation for a default-deny; must never be stored by any cache. |
| all other POST / DELETE (`/leagues`, `migrate`, `espn_members`, `claim-ownership`, `verify-membership`, delete) | `no-store` (middleware default) | Authenticated mutations / owner-gated reads; unsafe methods aren't cached by default but the header makes it explicit and future-proof. |
| `GET /health` | `no-store` (middleware default) | Non-sensitive liveness constant; harmless, and external monitors bypass caches. |

## Scope
- Header + cache middleware: `src/api/main.py` (`SECURITY_HEADERS`, `_security_headers`).
- Applies to **every** response (success and error) across the FastAPI app, ahead of the CORS
  and OTel-flush middleware in the stack; CORS headers ([main.py](../../../src/api/main.py)) and
  route-level `Cache-Control` are unaffected.
- **No** OpenAPI (`docs/api/openapi_spec.yaml`) or API Gateway / Terraform change — headers are
  applied at the application layer, not the contract or the gateway.

## Edge Cases
- **Route already set the header:** `setdefault` means a route's own `Cache-Control` (e.g.
  `query`'s `private, max-age=300`) is never overwritten by the default `no-store`.
- **Error responses (4xx/5xx):** still receive the security headers and the default `no-store`,
  since the middleware wraps the whole app and runs on every response.
- **CORS preflight (`OPTIONS`):** the security middleware sits outside CORS in the stack, so even
  a short-circuited preflight response is stamped.
- **Non-HTML nature:** the CSP/`X-Frame-Options`/HSTS headers are largely inert for a `fetch`ed
  JSON response; they matter only if a browser is coerced into rendering a response as a document.

## Acceptance Criteria
- [x] Every API response carries `X-Content-Type-Options: nosniff`, the `default-src 'none'` CSP
      with `frame-ancestors 'none'` and `base-uri 'none'`, `Strict-Transport-Security`, and
      `X-Frame-Options: DENY`.
- [x] Responses without a route-set `Cache-Control` default to `no-store` (verified on
      `POST /leagues/{id}/transfer-token`, which returns a secret).
- [x] `GET /leagues/{id}/query` retains `private, max-age=300` — the default does **not** override
      a route-set value.
- [x] Headers are applied by app middleware and cover error responses; no OpenAPI/Terraform change.

## Sources
`src/api/main.py` (`SECURITY_HEADERS`, `_security_headers`),
[FE-024](../frontend/FE-024-security-headers.md) (frontend-origin counterpart),
[BE-016](BE-016-league-ownership-authorization.md) (`transfer-token` secret handling).
