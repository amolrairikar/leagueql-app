# security-headers Specification

## Purpose
Stamp hardening security response headers on every API response via a single FastAPI middleware, and apply a default-deny `Cache-Control` policy so authenticated/private responses are never cacheable unless a route deliberately opts in. The API is a separate origin from the Cloudflare-served frontend and carries its own headers in application code.

## Requirements

### Requirement: Stamp security headers on every response
Every API response (success and error) SHALL carry `X-Content-Type-Options: nosniff`, a `default-src 'none'` CSP with `frame-ancestors 'none'` and `base-uri 'none'`, `Strict-Transport-Security`, and `X-Frame-Options: DENY`.

#### Scenario: Successful response
- **WHEN** the API returns a successful response
- **THEN** it carries `X-Content-Type-Options: nosniff`, the `default-src 'none'` CSP (with `frame-ancestors 'none'`, `base-uri 'none'`), `Strict-Transport-Security: max-age=63072000; includeSubDomains`, and `X-Frame-Options: DENY`

#### Scenario: Error and preflight responses
- **WHEN** the API returns a 4xx/5xx or a short-circuited `OPTIONS` preflight
- **THEN** the security headers are still stamped (the middleware wraps the whole app, ahead of CORS and OTel-flush)

### Requirement: Default-deny cache policy
The middleware SHALL set `Cache-Control: no-store` only when the handler did not set its own (`setdefault`), so route-level intent wins.

#### Scenario: Secret-bearing response defaults to no-store
- **WHEN** a route that does not set `Cache-Control` responds (e.g. `POST /leagues/{id}/transfer-token`, which returns a plaintext token)
- **THEN** the response defaults to `Cache-Control: no-store`

#### Scenario: Route-set cache value preserved
- **WHEN** `GET /leagues/{id}/query` sets `private, max-age=300`
- **THEN** the middleware does not override it

### Requirement: Application-layer only
The headers SHALL be applied by app middleware, with no OpenAPI or API Gateway/Terraform change.

#### Scenario: No contract change
- **WHEN** the headers are added
- **THEN** they cover every route uniformly at the application layer, and the OpenAPI contract and API Gateway configuration are unchanged
