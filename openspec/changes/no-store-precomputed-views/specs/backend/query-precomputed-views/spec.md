## RENAMED Requirements

- FROM: `### Requirement: Cache successful query responses`
- TO: `### Requirement: Query responses are not browser-cacheable`

## MODIFIED Requirements

### Requirement: Query responses are not browser-cacheable
The API SHALL set `Cache-Control: no-store` on successful query responses, so a browser never
independently re-serves precomputed-view data captured before a league was deleted, re-onboarded,
manually refreshed, or auto-refreshed.

#### Scenario: Cache header set
- **WHEN** a query succeeds
- **THEN** the response sets `Cache-Control: no-store`
