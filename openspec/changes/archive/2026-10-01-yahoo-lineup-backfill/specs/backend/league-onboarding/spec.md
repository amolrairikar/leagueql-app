# Spec Delta

## ADDED Requirements

### Requirement: Defer Yahoo weekly lineups to the lineup backfill
Yahoo onboarding and refresh SHALL NOT fetch per-team weekly rosters or player points. After a
successful Yahoo onboard or refresh, the onboarder SHALL mark the onboarded (or refreshed) seasons
as lineup-pending on the league's metadata and SHALL queue a lineup backfill for the league
(`backend/yahoo-lineup-backfill`).

#### Scenario: Onboard makes only core requests
- **WHEN** a Yahoo league is onboarded
- **THEN** the onboarder fetches each season's settings, standings, teams, draft results,
  transactions, week calendar, and weekly scoreboards, and no per-team weekly roster requests

#### Scenario: Seasons marked lineup-pending and backfill queued
- **WHEN** a Yahoo onboard completes with seasons 2018 through 2026 onboarded
- **THEN** all of those seasons are lineup-pending on the league's metadata and a lineup backfill
  is queued for the league

#### Scenario: Refresh marks the refreshed season pending
- **WHEN** a Yahoo league's current season is refreshed
- **THEN** that season is lineup-pending and a lineup backfill is queued for the league

#### Scenario: Refresh re-queues failed seasons
- **WHEN** a Yahoo league with seasons in its failed lineup seasons is refreshed
- **THEN** those seasons move back to lineup-pending and are included in the queued backfill

#### Scenario: Queueing failure does not fail the onboard
- **WHEN** the backfill cannot be queued after a successful onboard
- **THEN** the onboard still completes successfully, and the seasons stay lineup-pending until a
  later refresh queues the backfill

#### Scenario: Matchups carry their status
- **WHEN** a Yahoo scoreboard week is fetched
- **THEN** each stored matchup records whether it is not started, in progress, or finished

## REMOVED Requirements

### Requirement: Fetch Yahoo weekly rosters with player points per team
**Reason**: Fetching each team's roster for every week multiplied a Yahoo onboard's requests
(1,835 vs 319 for a 9-season, 12-team league) and triggered Yahoo `999` throttling that dropped
whole seasons. Weekly rosters and player points now come from the paced lineup backfill
(`backend/yahoo-lineup-backfill`). It is replaced by "Defer Yahoo weekly lineups to the lineup
backfill".
**Migration**: None. Seasons already onboarded with per-team rosters keep their lineups. Yahoo
leagues pick up the backfill on their next onboard or refresh.
