# Spec Delta

## Purpose
The `/power_rankings` page ranks every team in a season by a weekly power score that blends results with underlying strength, answering "who is actually good right now?". Everything is computed on the client from the season's `MATCHUPS` view; no backend support is needed. Rankings are shown per week, with movement since the previous week, a six-week rank trend, and a comparison against the team's rank by record alone.

## ADDED Requirements

### Requirement: Rank teams by a fixed-weight power score
`/power_rankings` SHALL rank every team in the selected season by a power score that is the weighted average of four components on a 0–100 scale: record 35%, points scored 30%, recent form 20%, and lineup efficiency 15%.

#### Scenario: Teams ordered by power score
- **WHEN** the page loads a season with played regular-season weeks
- **THEN** every team appears once, ordered by power score descending, with its rank, team name, manager, record, and power score

#### Scenario: Component scaling
- **WHEN** the power score is computed
- **THEN** record is the win percentage (ties count half) times 100, and points scored, recent form (mean of the last three played weeks), and lineup efficiency (points started divided by the points of the best possible lineup, summed over weeks with bench data) are each min–max scaled across teams so the best team scores 100 and the worst 0, or 50 for every team when all are equal

### Requirement: Count only played regular-season games
Power rankings SHALL be computed from played regular-season matchups only, excluding unplayed `0-0` placeholder weeks and every postseason game.

#### Scenario: Placeholder and playoff weeks ignored
- **WHEN** the season's matchups include a `0-0` future week and a playoff game
- **THEN** neither contributes to any team's record, points, form, or efficiency, and neither adds a selectable week

### Requirement: Show rankings going into a selected week
The page SHALL provide a "Week N" picker defaulting to the week after the last played regular-season week, where Week N ranks teams using every played regular-season game before week N. The picker SHALL offer each week from 2 through that default.

#### Scenario: Default week
- **WHEN** the last played regular-season week is 7
- **THEN** the picker shows "Week 8" and the table reflects games through week 7

#### Scenario: Stepping to an earlier week
- **WHEN** the user steps back to "Week 5"
- **THEN** the table is recomputed from games through week 4 only, and the previous-week control is disabled at the earliest week

#### Scenario: Season selection
- **WHEN** the user selects a different season
- **THEN** the page loads that season's matchups and resets the picker to its default week

### Requirement: Show movement and a six-week trend
Each team SHALL show how many places it moved since the previous week's rankings (up, down, or unchanged) and a trend of its rank over up to the last six weeks. At the earliest week, where there is no previous ranking, movement SHALL show as unchanged.

#### Scenario: Rank movement
- **WHEN** a team ranks 3rd this week and ranked 5th last week
- **THEN** its row shows an upward movement of 2

#### Scenario: First week has no movement
- **WHEN** the earliest available week is shown
- **THEN** no team shows movement and the trend contains a single point

### Requirement: Compare power rank with record rank
Each team SHALL show its rank by record alone (wins with ties as half, then points for) and a label of "Underrated" when its power rank is at least two places better than its record rank, "Overrated" when at least two places worse, and "On the mark" otherwise.

#### Scenario: Underrated team
- **WHEN** a team is 2nd by power but 5th by record
- **THEN** its row shows record rank `#5` labeled "Underrated"

### Requirement: Expand a team to see its breakdown
Clicking a team's row SHALL expand it to show each component's 0–100 score with its change since the previous week, the team's expected record, its previous rank, and a short written read on the team; clicking again SHALL collapse it.

#### Scenario: Expand and collapse
- **WHEN** the user expands a team's row
- **THEN** it shows the four component scores with week-over-week change, expected record, last week's rank, and a written read, and collapsing hides them

### Requirement: Degrade gracefully without bench data
When no team has bench data for the played weeks, the lineup-efficiency component SHALL be shown as unavailable and the power score SHALL be the weighted average of the remaining components with weights renormalized.

#### Scenario: Season without bench data
- **WHEN** the season's matchups carry no bench lists
- **THEN** the breakdown shows lineup efficiency as unavailable and the table still ranks every team

### Requirement: Explain the formula in a collapsible section
The page SHALL show a "How power rankings are calculated" section that is collapsed by default and expands and collapses when its header chevron is clicked, explaining each of the four components when expanded: its weight and how its 0–100 score is calculated, followed by a subsection explaining how league scaling works.

#### Scenario: Collapsed by default
- **WHEN** the page loads
- **THEN** the formula section shows only its header with a chevron, and the component descriptions are hidden

#### Scenario: Expand the formula section
- **WHEN** the user clicks the section's chevron
- **THEN** the section lists Record 35%, Points scored 30%, Recent form 20%, and Lineup efficiency 15%, each with a one-line description of how its 0–100 score is calculated, and clicking again hides them

#### Scenario: Scaling explanation
- **WHEN** the formula section is expanded
- **THEN** a "How scaling works" subsection shows the scaling formula, (value − lowest) ÷ (highest − lowest) × 100, a worked example table of four teams with their calculation and scaled score, and notes that the highest value scores 100 and the lowest 0, that equal values score 50, that scores are recalculated each week, and that the scaled score is then multiplied by the measure's weight

### Requirement: Handle empty and failed loads
The page SHALL show a loading skeleton while data loads, an empty message when the season has no played regular-season games, and an inline error alert when the matchups fail to load.

#### Scenario: No games played yet
- **WHEN** the selected season has no played regular-season games
- **THEN** the page shows a message that rankings appear once games have been played

#### Scenario: Load failure
- **WHEN** the matchups request fails
- **THEN** an inline error alert is shown instead of the table
