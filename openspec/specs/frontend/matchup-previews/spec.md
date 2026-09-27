# matchup-previews Specification

## Purpose

Give managers a pre-game head-to-head preview when they open a live-week (`0–0`) matchup on
`/matchups`, comparing the two teams' win probability, projected scoring, season stats, recent
form, scoring trend, and top players — all derived from the season's matchups, with no server
round-trip beyond the data the page already loads.

## Requirements

### Requirement: Open a matchup preview for a live-week matchup
Opening a live-week (`0–0`, unplayed) matchup on `/matchups` SHALL show a head-to-head matchup
preview for the two teams instead of a box score.

#### Scenario: Live-week matchup opens the preview
- **WHEN** the user opens a matchup whose two scores are both `0` (an unplayed, in-progress game)
- **THEN** a matchup preview comparing the two teams is shown instead of a box score

#### Scenario: Preview action label
- **WHEN** a live-week matchup card is displayed
- **THEN** its action reads "View matchup preview" rather than "View box score"

### Requirement: Win probability, projected score, and score distribution
The preview SHALL show each team's win probability and a single projected score, plus each team's
score distribution, derived from the team's season scoring (mean and consistency).

#### Scenario: Win probability and projection
- **WHEN** the preview is shown for two teams with played games this season
- **THEN** it shows each team's win probability (summing to 100%) and a single projected score

#### Scenario: Score distribution
- **WHEN** the preview is shown
- **THEN** each team's projected scoring is visualized as a distribution curve reflecting its mean
  and consistency

### Requirement: Head-to-head stat comparison
The preview SHALL compare the two teams across season stats including win percentage, average
points for, average points against, and highest score. Scoring consistency (σ) SHALL be shown
only once it is a distinct per-team value — that is, hidden while both teams share the identical
league-wide fallback σ (before either has enough games for its own standard deviation, roughly
the first few weeks) and shown once the two teams' σ differ.

#### Scenario: Stat comparison
- **WHEN** the preview is shown
- **THEN** the two teams are compared side by side on win percentage, average points for, average
  points against, and highest score

#### Scenario: Consistency hidden until it differs per team
- **WHEN** both teams still share the same fallback scoring consistency (σ), early in the season
- **THEN** the consistency row is omitted from the comparison, and it appears once the teams' σ
  values differ

### Requirement: Recent form
The preview SHALL show each team's recent results.

#### Scenario: Recent results
- **WHEN** the preview is shown for teams with played games
- **THEN** each team's most recent results (win/loss with the score) are listed

### Requirement: Points-by-week trend
The preview SHALL chart each team's points scored per week alongside the league average.

#### Scenario: Weekly points trend
- **WHEN** the preview is shown for teams with played weeks
- **THEN** a chart plots each team's points per week and the league average per week

### Requirement: Top scorers
The preview SHALL show each team's top scoring players this season, aggregated from the team's
matchup starters.

#### Scenario: Top players per team
- **WHEN** the preview is shown for teams with played games
- **THEN** each team's top scoring players for the season are listed with their position and points

### Requirement: Render gracefully with insufficient data
The preview SHALL render without error when there is little or no scoring history (for example the
first week of a season), falling back to a coin-flip win probability and omitting empty sections'
content rather than failing.

#### Scenario: No played games yet
- **WHEN** the preview is shown for a week in which neither team has any played games this season
- **THEN** the preview renders with a 50/50 win probability and empty trend/form/top-scorer
  sections, without error
