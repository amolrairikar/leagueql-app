## ADDED Requirements

### Requirement: Show each team's playoff odds
The projected-standings table SHALL show, for each team, a playoff-odds percentage equal to the share of possible remaining outcomes in which that team finishes in a top-`num_playoff_teams` seed. Each remaining matchup that the user has not picked SHALL be treated as an equally likely 50/50 outcome, points-for SHALL NOT be simulated (it stays fixed and only breaks ties), and the odds SHALL be conditional on the user's current picks — a picked matchup is locked to its picked result and only unpicked matchups vary. The odds SHALL be computed exactly by enumerating all outcome combinations when the number of unpicked matchups is small enough, and by sampling outcomes otherwise.

#### Scenario: Odds in the base view
- **WHEN** the standings table is shown with no picks made
- **THEN** each team's row shows a playoff-odds percentage computed over all possible results of the remaining matchups

#### Scenario: Equal-weight coin-flip outcomes
- **WHEN** exactly one regular-season matchup remains between two teams that are otherwise tied on record and points-for
- **THEN** each of those two teams shows 50% playoff odds

#### Scenario: Odds are conditional on picks
- **WHEN** the user picks a winner for a remaining matchup
- **THEN** that result is locked in and the playoff-odds column recomputes over only the still-unpicked matchups

#### Scenario: Clinched and eliminated extremes
- **WHEN** a team is in a top-`num_playoff_teams` seed regardless of any remaining result, or cannot reach one under any remaining result
- **THEN** its playoff odds read 100% or 0% respectively

#### Scenario: Large outcome space is sampled
- **WHEN** the number of unpicked matchups is too large to enumerate every combination
- **THEN** the playoff odds are estimated by sampling possible outcomes rather than left unshown
