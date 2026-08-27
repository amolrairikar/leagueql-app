## MODIFIED Requirements

### Requirement: Empty-state for no bracket
When the selected season has no bracket data, the page SHALL either render the interactive playoff-race predictor or a clear empty-state message, never the blank round columns. The predictor SHALL render only when the selected season is the latest season and its regular season is still in progress — there is at least one remaining (unplayed) regular-season week and no playoff matchup has been played. In every other no-bracket case a clear empty-state message SHALL render.

#### Scenario: In-progress season shows the predictor
- **WHEN** the `PLAYOFF_BRACKET#{season}` query returns no matches, the selected season is the latest season, and there is at least one unplayed regular-season week with no played playoff matchup
- **THEN** the playoff-race predictor renders in place of the empty-state message

#### Scenario: No playoffs yet
- **WHEN** the `PLAYOFF_BRACKET#{season}` query succeeds but returns no matches and the in-progress condition is not met (a past season, or the regular season is complete and awaiting playoffs)
- **THEN** a clear empty-state message renders instead of the blank round-column scaffold
