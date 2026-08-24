# app-stats-league-count Specification

## Purpose
Maintain and serve a global counter of how many leagues have been onboarded to LeagueQL. The counter lives in a single `LEAGUE_COUNT` item, incremented on successful onboarding and decremented on deletion. The public landing page reads this count (via `api.leagueql.com/counts`) as social proof.

## Requirements

### Requirement: Maintain the league count
The count SHALL increment by exactly 1 per successful new onboarding and decrement by exactly 1 per successful deletion, atomically under concurrency, without underflowing below zero.

#### Scenario: Onboard increments
- **WHEN** a new league is successfully onboarded
- **THEN** `LEAGUE_COUNT` increments by exactly 1

#### Scenario: Delete decrements
- **WHEN** a league is successfully deleted
- **THEN** `LEAGUE_COUNT` decrements by exactly 1 and never goes below zero in normal operation

#### Scenario: Concurrent updates
- **WHEN** onboards/deletes happen concurrently
- **THEN** the count is updated atomically (DynamoDB atomic counter)

### Requirement: Refresh and migrate do not change the count
Refresh and migration SHALL leave the count unchanged (same canonical league).

#### Scenario: Refresh/migrate
- **WHEN** a league is refreshed or migrated
- **THEN** `LEAGUE_COUNT` is unchanged

### Requirement: Serve the count to the landing page
The counts endpoint SHALL return the current value, and its CORS preflight SHALL permit W3C trace-context headers without edge-caching the preflight as the GET body.

#### Scenario: Counts value returned
- **WHEN** the landing page fetches the counts endpoint
- **THEN** it returns the current `LEAGUE_COUNT` value

#### Scenario: Preflight permits trace headers
- **WHEN** an `OPTIONS` preflight to `/counts` arrives carrying `traceparent`/`tracestate`
- **THEN** it returns `204` with `Access-Control-Allow-Headers` permitting those headers, and the preflight response is not edge-cached as the `GET` body
