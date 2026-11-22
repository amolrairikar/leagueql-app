# api-access-logging Specification

## Purpose
Record one structured API Gateway access-log entry per API request, including the authenticated caller's Clerk user ID, so support and security questions about who made a request can be answered from logs.

## Requirements

### Requirement: Access log identifies the authenticated caller
Every API Gateway access-log entry for a request that passed the Clerk JWT authorizer SHALL include the caller's verified Clerk user ID (the JWT `sub` claim) in a `userId` field, alongside the existing request fields.

#### Scenario: Authenticated request
- **WHEN** a request with a valid Clerk JWT is served (for example `GET /leagues/{id}`)
- **THEN** its access-log entry carries `userId` equal to the JWT's `sub`, plus the existing `requestId`, `path`, `status`, and timing fields

#### Scenario: Rejected non-member request is attributable
- **WHEN** an authenticated caller who is not the owner or a member of a gated league receives a `403` from `GET /leagues/{id}`
- **THEN** the access-log entry for that request records the status `403` together with that caller's `userId`

### Requirement: Unauthenticated requests log no user ID
A request that does not run the JWT authorizer (a public route) SHALL still be logged, with an empty or placeholder `userId` and no change to its other fields or to the response.

#### Scenario: Public route
- **WHEN** a request is served on a public route such as `GET /health` or the Yahoo OAuth callback
- **THEN** its access-log entry is written with an empty/placeholder `userId` and the request succeeds exactly as before

### Requirement: Existing access-log fields are preserved
Adding `userId` SHALL NOT remove or rename any existing access-log field, so queries and alarms built on those fields keep working.

#### Scenario: Backward-compatible format
- **WHEN** the access-log format is updated to include `userId`
- **THEN** `requestId`, `ip`, `userAgent`, `requestTime`, `requestTimeEpoch`, `httpMethod`, `routeKey`, `path`, `status`, `protocol`, `responseLength`, `responseLatency`, and `integrationLatency` are still present with unchanged meaning
