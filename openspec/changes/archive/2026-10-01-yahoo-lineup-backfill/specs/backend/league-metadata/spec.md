# Spec Delta

## ADDED Requirements

### Requirement: Report lineup data status
The league metadata response SHALL include `pending_lineup_seasons` and `failed_lineup_seasons`:
ascending-sorted season lists for seasons whose weekly lineups are still being backfilled or could
not be backfilled yet (`backend/yahoo-lineup-backfill`). Each list SHALL be empty when the league
has no such seasons.

#### Scenario: Seasons pending
- **WHEN** `GET /leagues/{leagueId}` is called for a Yahoo league whose 2024 and 2025 lineups are
  still being backfilled
- **THEN** the response includes `pending_lineup_seasons: ["2024", "2025"]` and
  `failed_lineup_seasons: []`

#### Scenario: Season failed
- **WHEN** a league's 2019 lineup backfill exhausted its retries
- **THEN** the response includes `"2019"` in `failed_lineup_seasons`

#### Scenario: No lineup status recorded
- **WHEN** the league's metadata has no lineup status (any ESPN or Sleeper league, or a fully
  backfilled Yahoo league)
- **THEN** both lists are returned empty
