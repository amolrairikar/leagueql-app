## ADDED Requirements

### Requirement: Filter matchup records by season phase

`/matchup_records` SHALL rank regular-season and postseason matchups separately via a
"Regular season / Postseason" switch that defaults to Regular season, so multi-week playoff
matchups never skew the regular-season boards.

#### Scenario: Postseason matchups excluded by default

- **WHEN** the page loads and the matchups include postseason games (`playoff_tier_type` other
  than `NONE`)
- **THEN** every record board is computed from regular-season matchups only and no postseason
  game is listed

#### Scenario: Toggling to Postseason

- **WHEN** the user switches the toggle to Postseason
- **THEN** every record board is computed from postseason matchups only, composed with the Season
  filter, and any open box score is closed
