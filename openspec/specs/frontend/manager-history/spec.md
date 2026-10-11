# manager-history Specification

## Purpose
The `/manager_history` page shows the year-to-year performance arc of each manager: per-season records and finishes, plus a rivalry tracker that classifies each opponent relationship as a domination, nemesis, or even rivalry based on head-to-head win rate.

## Requirements

### Requirement: Show per-season history
`/manager_history` SHALL show the selected manager's per-season records and finishes, including postseason games, with identities correct across migrated platforms, and render for a manager with only one season.

#### Scenario: Per-season records
- **WHEN** a manager is selected
- **THEN** their per-season records and finishes are shown, built from schedules that include winners/losers/consolation postseason games, with owner identities remapped across platforms

#### Scenario: Single-season manager
- **WHEN** the selected manager has only one season of history
- **THEN** the history renders with the limited data

### Requirement: Classify rivalries by win rate
The rivalry tracker SHALL classify opponents as domination (win rate ≥ 0.65), nemesis (< 0.40), or even, handling small samples so a single game is not misleading.

#### Scenario: Rivalry classification
- **WHEN** head-to-head win rates against opponents are computed
- **THEN** each opponent is classified domination / nemesis / even using the thresholds, with small-sample rivalries handled so a 1-game "rivalry" is not misleading

### Requirement: Exclude unplayed matchups from manager history

Per-manager results, high scores, and rivalry accumulators derived from matchups SHALL exclude
unplayed matchups — a matchup whose team scores are both exactly `0`.

#### Scenario: Unplayed matchup excluded from manager history

- **WHEN** a manager's matchups include an unplayed `0-0` week
- **THEN** it does not contribute to that manager's results, high scores, or rivalry totals

### Requirement: Show current standings position for an in-progress season

For a season with no finalized placement — a `final_rank` that is `0` (as ESPN reports
`rankCalculatedFinal` before a season is finalized) or absent — with at least one game
played, the per-season finish SHALL show the manager's current standings position
(derived from the regular-season record, ordered by wins then points-for) rather than a
rank of `0`. A champion or runner-up still resolves to a finish of 1st or 2nd; a season
with no games played yet shows no finish ("—").

#### Scenario: In-progress season shows current standings position

- **WHEN** a selected manager has an in-progress season whose row carries `final_rank: 0`
  and at least one played game
- **THEN** that season's finish renders as the manager's current standings position
  (ordered by wins, then points-for), not "0th place"

### Requirement: Omit the playoff-result pill for an in-progress season

A season card SHALL show the playoff-result pill ("Champion", "Runner-up", "Playoffs", or
"Missed Playoffs") only for a finalized season, meaning at least one team has a `final_rank`
≥ 1. For an in-progress season, the card SHALL omit the pill while still showing the season's
record, points, and current finish.

#### Scenario: In-progress season has no result pill

- **WHEN** a selected manager has an in-progress season where no team has a finalized
  `final_rank`
- **THEN** that season's card shows no "Champion", "Runner-up", "Playoffs", or
  "Missed Playoffs" pill

#### Scenario: Finalized season keeps its result pill

- **WHEN** a selected manager has a finalized season in which they won the championship
- **THEN** that season's card shows the "Champion" pill

### Requirement: Identify the runner-up from the title game
For a finalized season, a manager SHALL be the runner-up when their team lost the season's decided
winners-bracket matchup labeled "Finals", in whatever week that game was played.

#### Scenario: Runner-up of an early final
- **WHEN** a manager's team lost a finalized season's "Finals" winners-bracket game played in
  matchup period 15
- **THEN** that season's card shows the "Runner-up" pill and a 2nd-place finish when no
  `final_rank` is available

### Requirement: Expand a season inline to show its schedule
On `/manager_history`, each season card with at least one played game SHALL expand in place, without opening a
modal, to show that manager's week-by-week schedule and results for the season. Clicking the card again SHALL
collapse it.

#### Scenario: Expanding a season shows its schedule inline
- **WHEN** the user clicks a season card that has played games
- **THEN** the card expands to show that season's schedule and results, and no dialog opens

#### Scenario: Clicking an expanded season collapses it
- **WHEN** the user clicks the header of an expanded season card
- **THEN** the card collapses and its schedule is hidden

#### Scenario: Several seasons stay expanded
- **WHEN** the user expands one season and then another
- **THEN** both seasons remain expanded at the same time

#### Scenario: Selecting a game shows its box score inside the season
- **WHEN** the user clicks a game in an expanded season's schedule
- **THEN** that game's box score is shown inside the same season card

#### Scenario: A season with no games cannot be expanded
- **WHEN** a season card has no played games
- **THEN** the card is not expandable
