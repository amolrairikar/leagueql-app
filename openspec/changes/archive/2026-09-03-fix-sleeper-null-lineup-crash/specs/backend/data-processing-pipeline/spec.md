## MODIFIED Requirements

### Requirement: Tolerate empty and absent inputs
The processor SHALL write views without erroring when player metadata/stats or a Sleeper bracket are absent, when a Sleeper matchup entry's lineup fields (`starters`, `starters_points`, `players`, `players_points`) are null rather than merely omitted, guarding 0-column DuckDB registrations for views that can legitimately be empty.

#### Scenario: Missing player metadata
- **WHEN** `player_name`, `total_points`, or `position` is missing for some players
- **THEN** the affected views are still written with null fields rather than erroring

#### Scenario: Null Sleeper matchup lineup fields
- **WHEN** a Sleeper matchup entry carries a null value for `starters`, `starters_points`, `players`, or `players_points` (e.g. a team with no lineup set that week)
- **THEN** that team contributes no starter/bench stat rows for the matchup and the run completes without erroring, the same as when the field is absent or empty

#### Scenario: Empty bracket season
- **WHEN** a season's Sleeper `playoff_bracket`/`losers_bracket` raw data is empty or absent
- **THEN** no `PLAYOFF_BRACKET#{season}` item is written, its typical-playoff-week matchups are classified `playoff_tier_type = NONE`, and the run does not error

#### Scenario: Empty grouped view guard
- **WHEN** a legitimately-empty view still referenced downstream is registered (`brackets`, `transactions`, `player_scoring_totals`)
- **THEN** it is registered as a typed 0-row frame (numeric columns kept numeric) so DuckDB does not crash, and the `DRAFT` (SLEEPER) transform binds against an empty `player_scoring_totals` to yield draft rows with no scoring/VORP for that season

#### Scenario: Other empty view attribution
- **WHEN** any other view is unexpectedly empty at registration
- **THEN** it is logged by name before the failing registration so it is attributable from the logs
