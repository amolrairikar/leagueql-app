## RENAMED Requirements

- FROM: `### Requirement: Serialize numbers and cache the export response`
- TO: `### Requirement: Serialize numbers and mark the export response non-cacheable`

## MODIFIED Requirements

### Requirement: Serialize numbers and mark the export response non-cacheable
The export SHALL convert DynamoDB `Decimal` values to JSON numbers before serializing, and SHALL
set `Cache-Control: no-store` on a successful response so a browser never re-serves an export
captured before a league was deleted, re-onboarded, refreshed, or auto-refreshed.

#### Scenario: Decimals converted and cache header set
- **WHEN** an export request succeeds
- **THEN** numeric values are returned as JSON numbers and the response sets
  `Cache-Control: no-store`
