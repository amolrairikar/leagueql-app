## ADDED Requirements

### Requirement: Derive each season's playoff structure from league settings
The processor SHALL derive a season's playoff structure from its league settings: the first
playoff week is `playoff_week_start`, the number of winners-bracket rounds is
`ceil(log2(num_playoff_teams))`, and the final week is `playoff_week_start + rounds - 1`. Weeks
are in the platform's own matchup-week units. A season whose playoff start week or playoff-team
count was defaulted rather than supplied by the platform SHALL have no settings-derived structure.

#### Scenario: Two-week rounds counted in matchup periods
- **WHEN** an ESPN season has 13 regular-season matchup periods, 4 playoff teams, and
  two-week playoff rounds
- **THEN** its playoff structure has 2 rounds, a first playoff week of 14 and a final week of 15

#### Scenario: Six-team playoff with byes
- **WHEN** a season starts its playoffs in week 15 with 6 playoff teams
- **THEN** its playoff structure has 3 rounds and a final week of 17

#### Scenario: Defaulted settings yield no structure
- **WHEN** the platform payload for a season omits the playoff-team count or the playoff start week
- **THEN** that season has no settings-derived playoff structure and its labels and bracket rounds
  use the observed-weeks fallback

### Requirement: Label playoff rounds from the season's playoff structure
For ESPN and Yahoo, each winners-bracket matchup's `playoff_round` SHALL name its round counted
back from the season's final week: the final week is "Finals", the week before is "Semifinals",
and the week before that "Quarterfinals"; an earlier round is "Round N", counted from the first
playoff week. For Sleeper, the label SHALL be counted back the same way from the bracket's round
numbers. Labels SHALL NOT depend on fixed week numbers.

#### Scenario: Final played before week 17
- **WHEN** an ESPN season's settings put its final in matchup period 15 and its semifinals in
  period 14
- **THEN** the period-15 winners-bracket game is labeled "Finals" and the period-14
  winners-bracket games are labeled "Semifinals"

#### Scenario: Labels before the final is played
- **WHEN** a season with a settings-derived structure has played only its semifinal week
- **THEN** those games are labeled "Semifinals", and no game is labeled "Finals"

#### Scenario: Sleeper labels follow bracket rounds
- **WHEN** a Sleeper winners bracket has 3 rounds and a matchup pairs the two teams of a round-2
  bracket match
- **THEN** that matchup is labeled "Semifinals"

#### Scenario: Non-winners tiers keep their labels
- **WHEN** a playoff matchup is a winners-consolation or losers-tier game
- **THEN** it is labeled "Winners Consolation" or "Losers Bracket" as before, regardless of week

### Requirement: Fall back to observed playoff weeks when settings are defaulted
For a season without a settings-derived structure, the processor SHALL label winners-bracket
rounds from the observed winners-bracket weeks: once the last such week holds exactly one
winners-bracket game, rounds are counted back from it ("Finals", "Semifinals", …); otherwise
each week is labeled "Round N" counted from the first winners-bracket week.

#### Scenario: Completed season with defaulted settings
- **WHEN** a season with defaulted settings has winners-bracket games in two weeks and the later
  week holds a single game
- **THEN** that game is labeled "Finals" and the earlier week's games "Semifinals"

#### Scenario: In-progress season with defaulted settings
- **WHEN** a season with defaulted settings has winners-bracket games in only one week and that
  week holds two games
- **THEN** both games are labeled "Round 1" and neither is labeled "Finals"

### Requirement: Number ESPN and Yahoo bracket rounds from the playoff structure
For ESPN and Yahoo, each `PLAYOFF_BRACKET` match's `round` SHALL be its week's offset from the
first playoff week plus one, when the season has a settings-derived structure. Final placements
(`position` 1, 3 or 5) SHALL be assigned only to matches in the final round, so a
partly-played bracket carries no championship match. Without a structure, rounds and placements
SHALL follow the observed-weeks fallback.

#### Scenario: Semifinals are not the championship
- **WHEN** an ESPN season with 2 settings-derived rounds has played only its semifinal week
- **THEN** its bracket's semifinal matches have `round = 1` and no `position`, and no match has
  `position = 1`

#### Scenario: Completed bracket
- **WHEN** the same season's final has been played
- **THEN** the final has `round = 2` and `position = 1`, and its winner is the bracket's champion

## MODIFIED Requirements

### Requirement: Determine a single champion per season
The STANDINGS view SHALL mark as champion the winner of the decided winners-bracket game labeled
"Finals" in each season, for every platform. A season with no decided "Finals" game SHALL have no
champion.

#### Scenario: Exactly one champion
- **WHEN** a season with a completed winners bracket is processed
- **THEN** exactly one team in that season's standings has `champion = Yes`

#### Scenario: Playoffs ending before week 17
- **WHEN** a season's title game is played before week 17
- **THEN** that game's winner is marked as the season's champion

#### Scenario: Playoffs in progress
- **WHEN** a season's semifinals have been played but its final has not
- **THEN** no team in that season's standings has `champion = Yes`
