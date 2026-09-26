## ADDED Requirements

### Requirement: Show per-team playoff seed probabilities
Between the projected-standings table and the clinching-scenarios section, the predictor SHALL show a seed-probability table with one row per team and one column per playoff seed `1..num_playoff_teams`, plus a final "Miss" column for finishing outside the playoffs. Each cell SHALL show the share of possible remaining outcomes in which that team finishes in that exact seed (or, for the Miss column, outside the top-`num_playoff_teams` seeds), so each row sums to approximately 100%. The probabilities SHALL be computed over the same enumeration of remaining outcomes as the playoff odds — each un-picked matchup treated as an equally likely 50/50 outcome with points-for fixed and used only to break ties — and SHALL be conditional on the user's current picks. They SHALL be computed exactly by enumerating all outcome combinations when the number of un-picked matchups is small enough, and by sampling outcomes otherwise. The table SHALL be shown in both the live in-progress tool and the demo replay. When the playoff-team count was defaulted (platform omitted it), the table SHALL indicate the count is assumed.

#### Scenario: Seed distribution per team
- **WHEN** the seed-probability table is shown
- **THEN** each team's row shows, for every seed `1..num_playoff_teams` and a final Miss column, the probability of finishing in that seed across the remaining outcomes, and the row's values sum to approximately 100%

#### Scenario: Conditional on picks
- **WHEN** the user picks a winner for a remaining matchup
- **THEN** that result is locked in and the seed probabilities recompute over only the still-unpicked matchups

#### Scenario: Consistent with the playoff-odds column
- **WHEN** a team's seed probabilities and its playoff-odds percentage are both shown
- **THEN** the sum of the team's probabilities for seeds `1..num_playoff_teams` equals its playoff-odds percentage

#### Scenario: Large outcome space is sampled
- **WHEN** the number of unpicked matchups is too large to enumerate every combination
- **THEN** the seed probabilities are estimated by sampling possible outcomes rather than left unshown

#### Scenario: Shown in demo replay
- **WHEN** the predictor runs in replay mode over a completed season
- **THEN** the seed-probability table is shown for that season's teams

## MODIFIED Requirements

### Requirement: Show each team's playoff odds
The projected-standings table SHALL show, for each team, a playoff-odds percentage equal to the share of possible remaining outcomes in which that team finishes in a top-`num_playoff_teams` seed, which SHALL equal the sum of the team's probabilities for seeds `1..num_playoff_teams` in the seed-probability table. Each remaining matchup that the user has not picked SHALL be treated as an equally likely 50/50 outcome, points-for SHALL NOT be simulated (it stays fixed and only breaks ties), and the odds SHALL be conditional on the user's current picks — a picked matchup is locked to its picked result and only unpicked matchups vary. The odds SHALL be computed exactly by enumerating all outcome combinations when the number of unpicked matchups is small enough, and by sampling outcomes otherwise.

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
