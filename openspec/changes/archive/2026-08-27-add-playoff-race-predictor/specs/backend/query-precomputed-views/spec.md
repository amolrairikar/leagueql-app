## ADDED Requirements

### Requirement: Expose the league settings view
The API SHALL serve the per-season league settings view through the `LEAGUE_SETTINGS` `queryType`, returning the stored `LEAGUE_SETTINGS#{season}` item's `data` for a season-suffixed query.

#### Scenario: League settings query
- **WHEN** `queryType=LEAGUE_SETTINGS#{season}` is queried for an onboarded league
- **THEN** the API returns the season's `num_playoff_teams`, `playoff_week_start`, and `regular_season_weeks` with `200`

#### Scenario: League settings missing
- **WHEN** `queryType=LEAGUE_SETTINGS#{season}` is queried and no such item exists
- **THEN** the API returns `404` "No data found for the requested query"
