# BE-005: Query Precomputed Views API

## Description
Serves precomputed league views to the frontend. `GET /leagues/{leagueId}/query` resolves
the platform league ID to its canonical league ID, maps the `queryType` to a DynamoDB sort
key, and returns the stored `data`. Season-scoped views require a season suffix
(e.g. `STANDINGS#2024`); cross-season/collection views use a prefix query that paginates
and concatenates all matching items.

## Scope
- Endpoint: `GET /leagues/{leagueId}/query?platform=&queryType=` (`src/api/routes.py::query_league`).
- Query types (`QueryType`): `TEAMS`, `MATCHUPS`, `SEASON_STANDINGS`, `WEEKLY_STANDINGS`,
  `PLAYOFF_BRACKET`, `DRAFT`, `TRANSACTIONS` (Sleeper-only;
  [BE-019](BE-019-sleeper-transactions.md)), `PLATFORM_MIGRATION`.
- Mapping: `QUERY_TYPE_TO_SK_BASE` (`src/api/main.py`).

## Edge Cases
- **`queryType` with vs. without suffix:** `STANDINGS#2024` → exact `get_item`;
  bare `MATCHUPS` → `begins_with` prefix query with pagination over `LastEvaluatedKey`.
- **Invalid `queryType`:** return `400` with a documentation pointer.
- **League not onboarded:** lookup miss returns `404`.
- **No data for a valid query:** return `404` "No data found for the requested query".
- **Decimal conversion:** DynamoDB `Decimal` values must be converted to native
  numbers before serialization (`convert_decimals`).
- **Case-insensitive query type:** `QueryType` accepts case-insensitive input.
- **Large collections:** prefix queries must paginate fully (not just the first page).

## Caching
- Successful query responses set `Cache-Control: private, max-age=300` (5 min browser cache).
- Polling-style calls (job status, league metadata) must use `no-store` (handled by their
  own endpoints, not this one).

## Acceptance Criteria
- [ ] A valid suffixed `queryType` returns the single matching item's `data` with `200`.
- [ ] A valid unsuffixed `queryType` returns all matching items' `data` concatenated, fully
      paginated, with `200`.
- [ ] An unrecognized `queryType` returns `400`.
- [ ] An un-onboarded league returns `404`; a valid query with no stored item returns `404`.
- [ ] All `Decimal` values are converted to JSON-safe numbers.
- [ ] Successful responses set `Cache-Control: private, max-age=300`.

## Authorization (BE-016)
ESPN queries are **member-gated** ([BE-016](BE-016-league-ownership-authorization.md)) — a non-member gets `403`. Sleeper queries stay open to any authenticated caller.

## Sources
`src/api/routes.py::query_league`, `src/api/main.py` (`QueryType`, `QUERY_TYPE_TO_SK_BASE`),
`docs/api/openapi_spec.yaml`.
