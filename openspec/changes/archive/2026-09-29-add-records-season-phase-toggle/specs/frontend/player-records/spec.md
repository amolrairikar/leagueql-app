## ADDED Requirements

### Requirement: Filter player records by season phase

`/player_records` SHALL rank regular-season and postseason performances separately via a
"Regular season / Postseason" switch that defaults to Regular season, so multi-week playoff
matchups never skew the regular-season boards.

#### Scenario: Postseason performances excluded by default

- **WHEN** the page loads and the matchups include postseason games (`playoff_tier_type` other
  than `NONE`)
- **THEN** the boards are computed from regular-season matchups only and no postseason
  performance is listed

#### Scenario: Toggling to Postseason

- **WHEN** the user switches the toggle to Postseason
- **THEN** the boards are computed from postseason matchups only, composed with the Season and
  Manager filters, and any open box score is closed
