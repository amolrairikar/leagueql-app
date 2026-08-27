# playoff-bracket Specification

## Purpose
The `/playoff_bracket` page renders the winners'-bracket playoff tree for a selected season, including seeding, per-round matchups with scores, and final placements (champion, runner-up, etc.). Scores are joined from the matchups views; seeding lines are derived from each match's `team_*_from` references.

## Requirements

### Requirement: Render the bracket for a season
`/playoff_bracket` SHALL render the bracket for the selected season with rounds, seeds, matchup scores, and final placements, drawing advancement lines from `team_*_from` seeding references.

#### Scenario: Bracket render
- **WHEN** a season with playoff data is selected
- **THEN** the bracket renders with rounds, seeds (from the last `WEEKLY_STANDINGS` snapshot), matchup scores, final placements, and advancement lines reflecting `team_*_from` references

#### Scenario: Wildcard reconstruction
- **WHEN** a source (e.g. Sleeper) omits early-round `from` links (reconstructed server-side)
- **THEN** the wildcard round renders its matchups (not only bye cards), pairing each bye team with the wildcard match feeding its semifinal

### Requirement: Derive championship week from data
The championship week SHALL be derived from real matchup data, not hard-coded.

#### Scenario: Variable championship week
- **WHEN** the bracket is rendered
- **THEN** the championship week is derived from actual matchup data (handling week 17 vs 18, etc.)

### Requirement: Match scores regardless of team order
Scores SHALL be correctly matched to bracket matches regardless of team order in the source data, with unplayed matches rendered as TBD.

#### Scenario: Score join
- **WHEN** bracket matches are joined to matchups
- **THEN** scores are matched correctly for either team order

#### Scenario: Unplayed match
- **WHEN** a match's `winner`/`loser` is null (not yet played)
- **THEN** it renders as TBD without error

### Requirement: Empty-state for no bracket
When the selected season has no bracket data, the page SHALL either render the interactive playoff-race predictor or a clear empty-state message, never the blank round columns. The predictor SHALL render only when the selected season is the latest season and its regular season is still in progress — there is at least one remaining (unplayed) regular-season week and no playoff matchup has been played. In every other no-bracket case a clear empty-state message SHALL render.

#### Scenario: In-progress season shows the predictor
- **WHEN** the `PLAYOFF_BRACKET#{season}` query returns no matches, the selected season is the latest season, and there is at least one unplayed regular-season week with no played playoff matchup
- **THEN** the playoff-race predictor renders in place of the empty-state message

#### Scenario: No playoffs yet
- **WHEN** the `PLAYOFF_BRACKET#{season}` query succeeds but returns no matches and the in-progress condition is not met (a past season, or the regular season is complete and awaiting playoffs)
- **THEN** a clear empty-state message renders instead of the blank round-column scaffold
