## Purpose

The playoff-race predictor lets a manager pick the winners of the remaining regular-season matchups and watch a projected standings table re-sort live around the playoff cutoff, turning the pre-playoff Playoff Bracket page into an interactive "who makes it" tool.

## ADDED Requirements

### Requirement: Pick winners of remaining regular-season matchups
The predictor SHALL let the user select a winner for each pickable matchup by clicking a team, SHALL let the user clear that pick by clicking the selected winner again, and SHALL provide a control that resets all picks. Matchups left unpicked SHALL NOT affect the projection.

#### Scenario: Pick a winner
- **WHEN** the user clicks a team in a pickable matchup
- **THEN** that team is marked the winner and the projected standings update to include the result

#### Scenario: Unpick by reclicking
- **WHEN** the user clicks a team that is already the selected winner of its matchup
- **THEN** the pick is cleared and the projected standings revert that matchup's effect

#### Scenario: Reset all picks
- **WHEN** the user activates the reset control
- **THEN** every pick is cleared and the standings return to the baseline (records through the last completed regular-season week)

### Requirement: Project standings live from picks
The predictor SHALL render a standings table ordered by projected wins descending, then points-for descending, that updates whenever a pick changes. Points-for SHALL be the season-to-date total used only as a tiebreaker.

#### Scenario: Standings re-sort on a pick
- **WHEN** a pick changes a team's projected record enough to change the order
- **THEN** the standings table re-sorts to reflect projected wins (ties broken by points-for)

#### Scenario: Movement versus current standings
- **WHEN** a team's projected seed differs from its baseline seed
- **THEN** the row shows an up/down movement indicator of the seed change

### Requirement: Show the playoff cutoff line
The standings table SHALL draw a cutoff line after the league's configured number of playoff teams, visually distinguishing seeds that would make the playoffs. When the playoff-team count was not provided by the platform and a default was used, the cutoff SHALL be labeled as assumed.

#### Scenario: Cutoff at configured count
- **WHEN** the league settings report `num_playoff_teams`
- **THEN** the cutoff line is drawn after that many seeds and those seeds are marked as making the playoffs

#### Scenario: Assumed cutoff note
- **WHEN** the playoff-team count was defaulted (platform omitted it)
- **THEN** the cutoff is labeled to indicate the count is assumed

#### Scenario: Clinched seed
- **WHEN** a team has secured a top-`num_playoff_teams` seed by wins alone regardless of any remaining pick
- **THEN** its row shows a clinched indicator

### Requirement: Show each team's record entering the week
Each team card in a matchup SHALL display the team's record entering that week — its baseline record plus the results of the user's picks in earlier weeks only. A pick in the current week SHALL NOT change the record shown on that same card.

#### Scenario: Record reflects earlier-week picks
- **WHEN** the user picks winners in an earlier week and advances to a later week
- **THEN** the later week's team cards show records that include those earlier picks

### Requirement: Step through remaining weeks one at a time
The predictor SHALL present the pickable matchups grouped by week and let the user move between weeks one at a time, showing for each week how many of its matchups have been picked.

#### Scenario: Week navigation
- **WHEN** the user moves to another remaining week
- **THEN** only that week's matchups are shown, with an indication of how many are picked

### Requirement: Only remaining regular-season matchups are pickable
The predictor SHALL only make regular-season matchups within the league's regular season (week ≤ `regular_season_weeks`) pickable; playoff matchups and weeks after the regular season SHALL NOT be pickable. In a live in-progress season the pickable set is the unplayed regular-season weeks; in a demo replay it is the last three regular-season weeks presented unpicked.

#### Scenario: Live in-progress season
- **WHEN** the predictor runs for an in-progress season
- **THEN** the pickable matchups are the unplayed (both scores `0`) regular-season matchups bounded by `regular_season_weeks`

#### Scenario: Playoff weeks excluded
- **WHEN** the matchup data includes weeks at or after the playoff start
- **THEN** those weeks are never pickable and never contribute to the projected regular-season standings

#### Scenario: Demo replay
- **WHEN** the predictor runs in replay mode over a completed season
- **THEN** it presents the last three regular-season weeks as pickable (unpicked) with the baseline being records entering that window
