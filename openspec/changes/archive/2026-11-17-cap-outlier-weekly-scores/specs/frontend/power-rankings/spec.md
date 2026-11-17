## MODIFIED Requirements

### Requirement: Rank teams by a fixed-weight power score
`/power_rankings` SHALL rank every team in the selected season by a power score that is the weighted average of four components on a 0–100 scale: record 35%, points scored 30%, recent form 20%, and lineup efficiency 15%. Weekly scores feeding points scored and recent form SHALL be capped at the league median plus two robust standard deviations (1.4826 × the median absolute deviation of all played team-weeks through the cut week) so a single outlier week cannot dominate.

#### Scenario: Teams ordered by power score
- **WHEN** the page loads a season with played regular-season weeks
- **THEN** every team appears once, ordered by power score descending, with its rank, team name, manager, record, and power score

#### Scenario: Component scaling
- **WHEN** the power score is computed
- **THEN** record is the win percentage (ties count half) times 100, and points scored, recent form (mean of the last three played weeks), and lineup efficiency (points started divided by the points of the best possible lineup, summed over weeks with bench data) are each min–max scaled across teams so the best team scores 100 and the worst 0, or 50 for every team when all are equal

#### Scenario: Outlier weeks are capped
- **WHEN** a team's weekly score exceeds the league median plus two robust standard deviations of all played team-weeks through the cut week
- **THEN** that week counts as the cap value in the points-scored and recent-form components (record, lineup efficiency, displayed record and points-for tiebreaks use the actual score), so one freak week cannot lift a weak team far up the rankings
