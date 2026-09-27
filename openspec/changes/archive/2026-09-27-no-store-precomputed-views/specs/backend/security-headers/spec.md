## MODIFIED Requirements

### Requirement: Default-deny cache policy
The middleware SHALL set `Cache-Control: no-store` only when the handler did not set its own (`setdefault`), so route-level intent wins.

#### Scenario: Secret-bearing response defaults to no-store
- **WHEN** a route that does not set `Cache-Control` responds (e.g. `POST /leagues/{id}/transfer-token`, which returns a plaintext token)
- **THEN** the response defaults to `Cache-Control: no-store`

#### Scenario: Route-set cache value preserved
- **WHEN** a route sets its own `Cache-Control` (e.g. `GET /feature-flags` sets `no-store`)
- **THEN** the middleware preserves that value rather than re-applying its own
