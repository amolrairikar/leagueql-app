# Spec Delta

## Purpose

A personal `/my_team` page. A signed-in manager claims their team once, then sees *their* current
week at a glance: how last week went, where they stand, their playoff odds and how those moved,
their lineup efficiency, and this week's matchup. Everything is computed client-side from the
league's existing data.

## ADDED Requirements

### Requirement: Claim a team
When the caller has not claimed a team, or their claimed owner has no team in the current season,
the page SHALL show a "Which team is yours?" picker. The picker SHALL list every team in the
current season with its team name and owner username. Choosing a team and selecting "Save my
team" SHALL save that team's owner as the caller's claim and then show the Your week card for
it. If saving fails, the picker SHALL stay open and show an inline error.

#### Scenario: First visit
- **WHEN** a user with no claimed team opens `/my_team`
- **THEN** the page shows the "Which team is yours?" picker listing the current season's teams, and no Your week card

#### Scenario: Save a claim
- **WHEN** the user selects a team and chooses "Save my team"
- **THEN** the claim is saved and the page shows the Your week card for that team

#### Scenario: Claimed owner absent from the current season
- **WHEN** the user's saved claim names an owner who has no team in the current season
- **THEN** the page shows the picker again

#### Scenario: Save fails
- **WHEN** saving the claim returns an error
- **THEN** an inline error is shown and the picker stays open with the selection kept

### Requirement: Change the claimed team
The Your week card SHALL offer a "Change team" action that reopens the picker with the current
team preselected. Saving a different team SHALL update the card to that team.

#### Scenario: Change team
- **WHEN** a user viewing their Your week card chooses "Change team", selects a different team, and saves
- **THEN** the card shows the newly selected team

### Requirement: Show the claimed team's week
For a claimed team in a season that is in progress, the page SHALL show a Your week card with the
team name, owner username and current week number, containing:
- **Last week:** the result (W/L/T) and the team's score, the opponent's score, and the margin.
- **Record:** the team's regular-season record, its rank among the league's teams (wins, then
  points for), and its points for.
- **Playoff odds:** the team's current chance of making the playoffs, as a whole-number
  percentage, and its change in percentage points since before last week's games.
- **Lineup efficiency:** the season-long efficiency (actual starter points ÷ optimal starter
  points, summed over every played regular-season week that has lineup data), as a whole-number
  percentage, and the points left on the bench last week.
- **Weekly awards:** the awards the team won last week, and how many Highest Score awards it has
  won this season. Awards are not summed into a single total, because they mix desirable and
  undesirable outcomes (for example Lowest Score and Worst Win).

Each metric's value SHALL match what the corresponding existing page shows for the same team and
week: Matchups, the playoff race predictor, and the box-score lineup-efficiency chip.

#### Scenario: Metrics for an in-progress season
- **WHEN** a user with a claimed team opens `/my_team` in Week 8 of an in-progress season
- **THEN** the card shows "Week 8", last week's result and margin, the record with rank and points for, the playoff odds with their change since before Week 7's games, the season lineup efficiency with Week 7's bench points, and last week's awards with the season's Highest Score count

#### Scenario: Odds change direction
- **WHEN** the team's playoff odds rose from 66% before last week's games to 78% now
- **THEN** the playoff odds tile shows 78% and a rise of 12 percentage points

### Requirement: Show this week's matchup
The card SHALL show the claimed team's matchup for the current week against its opponent, with
the two projected scores and each side's win probability. It SHALL also show the all-time
head-to-head record between the two managers across every season (with managers matched across
platform migrations), the result of their most recent meeting, and the opponent's last three
results. It SHALL link to the full matchup preview on the Matchups page. When the team has no
matchup this week, it SHALL show a "No matchup this week" message instead.

#### Scenario: Matchup with history
- **WHEN** the claimed team plays an opponent it has met 10 times before (6 wins, 4 losses)
- **THEN** the matchup panel shows both projected scores, both win probabilities, "6–4" as the all-time head-to-head, the most recent meeting's result, and the opponent's last three results

#### Scenario: No matchup this week
- **WHEN** the claimed team has no matchup in the current week (for example, a playoff bye or elimination)
- **THEN** the matchup panel shows "No matchup this week"

### Requirement: Handle season boundaries
In Week 1, before any game is played, the card SHALL show no last-week result, SHALL show the
efficiency and odds change as unavailable, and SHALL show an even 50% win probability. When the
current season has no remaining matchups (the offseason), the card SHALL show the team's final
result for that season (final record and final standing) instead of a current week.

#### Scenario: Week 1
- **WHEN** a user with a claimed team opens `/my_team` before any game of the season has been played
- **THEN** the card shows no last-week result, efficiency and odds change are shown as unavailable, and the matchup shows a 50% win probability for each side

#### Scenario: Offseason
- **WHEN** a user with a claimed team opens `/my_team` after every matchup of the latest season has been played
- **THEN** the card shows that season's final record and final standing for the team instead of a current-week view

### Requirement: Email placeholder
The card SHALL show an "Email me each week" row with a "COMING SOON!" label and a disabled switch
in the off position. The switch SHALL NOT be operable and SHALL NOT send any request.

#### Scenario: Placeholder cannot be toggled
- **WHEN** the user tries to activate the "Email me each week" switch
- **THEN** the switch stays off, it is exposed as disabled, and no request is sent

### Requirement: Loading and errors
The page SHALL show skeleton placeholders while its data loads. If loading the claim or the
league's data fails, the page SHALL show an inline error in place of the card or picker, and
the rest of the app SHALL keep working.

#### Scenario: Loading
- **WHEN** the claim or league data is still loading
- **THEN** skeleton placeholders are shown

#### Scenario: Claim load fails
- **WHEN** reading the caller's claim returns a `4xx` or `5xx`
- **THEN** an inline error is shown in place of the picker and card

#### Scenario: League data load fails
- **WHEN** the league's matchups fail to load
- **THEN** an inline error is shown in place of the card

#### Scenario: League settings unavailable
- **WHEN** the league's settings fail to load but its matchups load
- **THEN** the card still renders, with playoff odds computed using the playoff race predictor's default cutoff

### Requirement: Demo mode
In demo mode the page SHALL work without a backend claim: it SHALL default to the first team in
the demo league, SHALL let the user change the team for the current session only, and SHALL NOT
persist the choice.

#### Scenario: Demo defaults to a team
- **WHEN** a demo-mode user opens `/my_team`
- **THEN** the Your week card is shown for the demo league's first team without showing the picker first

#### Scenario: Demo change is not persisted
- **WHEN** a demo-mode user changes the team and reloads the page
- **THEN** the page shows the demo league's first team again
