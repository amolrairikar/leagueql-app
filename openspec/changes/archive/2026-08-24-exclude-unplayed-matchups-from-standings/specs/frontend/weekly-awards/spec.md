## ADDED Requirements

### Requirement: Exclude unplayed matchups from awards

Weekly awards, the running per-manager award tally, and win streaks SHALL exclude unplayed
matchups — a matchup whose team scores are both exactly `0` — so a placeholder future game never
wins an award (for example "Lowest Score") or affects a streak.

#### Scenario: Unplayed matchup excluded from awards

- **WHEN** a week's matchups include an unplayed `0-0` game
- **THEN** it is not eligible for any award, is not counted in the running tally, and does not
  affect win streaks
