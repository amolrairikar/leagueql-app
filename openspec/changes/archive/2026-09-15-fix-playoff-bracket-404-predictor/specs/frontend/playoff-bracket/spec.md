## MODIFIED Requirements

### Requirement: Empty-state for no bracket
When the selected season has no bracket data, the page SHALL either render the interactive playoff-race predictor or a clear empty-state message, never the blank round columns. A `PLAYOFF_BRACKET#{season}` query that responds with the backend's "no data" `404` SHALL be treated as no bracket matches (the same as a successful empty response), not as a load error. The predictor SHALL render only when the selected season is the latest season and its regular season is still in progress — there is at least one remaining (unplayed) regular-season week and no playoff matchup has been played. In every other no-bracket case a clear empty-state message SHALL render. A non-`404` failure of the bracket query (e.g. `5xx`) SHALL still surface the feature's fallback error message.

#### Scenario: In-progress season shows the predictor
- **WHEN** the `PLAYOFF_BRACKET#{season}` query returns no matches, the selected season is the latest season, and there is at least one unplayed regular-season week with no played playoff matchup
- **THEN** the playoff-race predictor renders in place of the empty-state message

#### Scenario: No-data 404 is treated as no matches
- **WHEN** the `PLAYOFF_BRACKET#{season}` query responds with the backend's "no data" `404` for the latest in-progress season
- **THEN** the page treats the bracket as having no matches and renders the playoff-race predictor, never the raw error message

#### Scenario: No playoffs yet
- **WHEN** the `PLAYOFF_BRACKET#{season}` query returns no matches (including via the "no data" `404`) and the in-progress condition is not met (a past season, or the regular season is complete and awaiting playoffs)
- **THEN** a clear empty-state message renders instead of the blank round-column scaffold

#### Scenario: Bracket load error still surfaces
- **WHEN** the `PLAYOFF_BRACKET#{season}` query fails with a non-`404` status (e.g. `5xx`)
- **THEN** the feature's fallback error message renders instead of the predictor or empty-state
