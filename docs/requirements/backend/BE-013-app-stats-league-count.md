# BE-013: App Stats / League Count

## Description
Maintains and serves a global counter of how many leagues have been onboarded to LeagueQL.
The counter is stored in a single `LEAGUE_COUNT` item and is incremented on successful
onboarding and decremented on deletion. The public landing page reads this count (via
`api.leagueql.com/counts`) as social proof.

## Scope
- Item: `APP#STATS` / `LEAGUE_COUNT` (`docs/db/dynamodb_spec.md`).
- Writers: `update_league_count` — incremented after onboard ([BE-001](BE-001-league-onboarding.md)),
  decremented after delete ([BE-007](BE-007-delete-league-api.md)).
- Consumer: landing page fetch of `https://api.leagueql.com/counts`
  ([FE-001](../frontend/FE-001-landing-page.md)).

## Edge Cases
- **Concurrent onboards/deletes:** count updates must be atomic (DynamoDB atomic counter).
- **Refresh / migrate:** must NOT change the count (same canonical league).
- **Counter underflow:** deletion must not drive the count below zero in normal operation.
- **Counts endpoint unavailable:** the landing page must degrade gracefully (hide/placeholder).

## Acceptance Criteria
- [ ] `LEAGUE_COUNT` increments by exactly 1 per successful new onboarding.
- [ ] `LEAGUE_COUNT` decrements by exactly 1 per successful deletion.
- [ ] Refresh and migration leave the count unchanged.
- [ ] Updates are atomic under concurrency.
- [ ] The counts endpoint returns the current value for the landing page.

## Sources
`docs/db/dynamodb_spec.md` (LEAGUE_COUNT), `src/api/routes.py` (`update_league_count`).
