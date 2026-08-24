# weekly-awards Specification

## Purpose
A free section on the `/matchups` page that auto-generates a per-week awards reel plus a running, week-to-date tally of how many awards each manager has collected. Everything is computed entirely client-side from the season's `MATCHUPS` view. The section tracks the page's existing week navigation: award cards reflect the selected week; the tally accumulates across weeks `1 … selectedWeek`.

## Requirements

### Requirement: Show weekly award cards
`/matchups` SHALL render one card per award type for the selected week below the matchup grid, recomputing on week navigation, and rendering for everyone.

#### Scenario: Award cards
- **WHEN** a week is selected on `/matchups`
- **THEN** cards render for Highest Score, Lowest Score, Biggest Blowout, Narrowest Win, Best Loss, and Worst Win for that week, recomputing when navigating to a different week; the section renders for everyone

#### Scenario: No eligible winner
- **WHEN** an award type has no computable winner (e.g. every game tied)
- **THEN** that card shows an em dash and "No award this week" rather than a blank

### Requirement: Show a week-to-date tally with streaks
A tally table SHALL list each manager with per-award-type counts (no combined total) accumulated across weeks `1 … selectedWeek`, sorted alphabetically, and surface the longest active win streak (length ≥ 2).

#### Scenario: Tally
- **WHEN** the tally renders through the selected week
- **THEN** each manager has per-award-type counts (no combined total), sorted alphabetically by manager, and the longest active win streak holder (length ≥ 2) through the selected week is surfaced

### Requirement: Compute awards over all played weeks with deterministic ties
Awards SHALL be computed for every week present in `MATCHUPS` (regular season and playoffs), excluding ties/byes/self-matchups from win/loss-based awards, with deterministic tie-breaking.

#### Scenario: Exclusions
- **WHEN** a week contains byes, self-matchup placeholders (`team_a_id === team_b_id`), or tied matchups
- **THEN** byes and self-matchups produce no award, and ties are excluded from blowout/narrowest/best-loss/worst-win (both teams still compete for highest/lowest score)

#### Scenario: Playoff weeks and in-progress season
- **WHEN** postseason weeks are navigated or the season is in progress
- **THEN** awards are computed for the teams that played that week, and the tally reflects only weeks played through the selected week

### Requirement: Handle load failures and empty data
A `MATCHUPS` load failure SHALL render an inline message and a season with no matchup data an empty-state message, never crashing.

#### Scenario: Failure or empty
- **WHEN** the `MATCHUPS` query fails (404/error) or the season has no matchup data
- **THEN** an inline message or empty-state message renders instead of a crash
