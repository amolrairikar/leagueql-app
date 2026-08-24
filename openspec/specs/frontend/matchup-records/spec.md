# matchup-records Specification

## Purpose
The `/matchup_records` page surfaces all-time team/matchup superlatives across league history: Highest Team Score, Lowest Team Score, Highest Matchup Score (combined), Lowest Matchup Score, Biggest Blowout (largest margin), and Closest Game (smallest margin).

## Requirements

### Requirement: Show the six record categories
`/matchup_records` SHALL show all six record categories, each with the team(s), season, and week of the record.

#### Scenario: Record categories
- **WHEN** the page loads
- **THEN** it shows Highest/Lowest Team Score, Highest/Lowest Matchup Score, Biggest Blowout, and Closest Game, each linking to the owner/team, season, and week

### Requirement: Rank team-games independently
Highest/Lowest Team Score SHALL rank both sides of a matchup as independent team-game candidates, so a single matchup can occupy multiple leaderboard slots.

#### Scenario: Both sides ranked
- **WHEN** the two highest (or lowest) team scores of a season were played against each other
- **THEN** both appear as independent candidates and can occupy multiple slots in the leaderboard

### Requirement: Compute margins with ties handled
Biggest Blowout and Closest Game SHALL use point margin with ties handled, and combined matchup scores computed correctly.

#### Scenario: Margin records
- **WHEN** the margin records are computed
- **THEN** Biggest Blowout uses the largest margin and Closest Game the smallest (handling a zero-margin tie), and Highest/Lowest Matchup Score use the combined two-team total

### Requirement: Exclude incomplete matchups
Unplayed/in-progress matchups SHALL NOT produce false records.

#### Scenario: In-progress week
- **WHEN** matchups are incomplete or have zero scores
- **THEN** they are excluded so they do not pollute the records
