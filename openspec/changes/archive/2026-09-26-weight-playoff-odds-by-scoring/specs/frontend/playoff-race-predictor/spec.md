# Spec Delta

## MODIFIED Requirements

### Requirement: Show each team's playoff odds
The projected-standings table SHALL show, for each team, a playoff-odds percentage equal to the share of possible remaining outcomes in which that team finishes in a top-`num_playoff_teams` seed, which SHALL equal the sum of the team's per-seed probabilities for seeds `1..num_playoff_teams` shown in the same table. Each remaining matchup that the user has not picked SHALL be weighted by the probability that each team wins it, derived from the two teams' regular-season scoring distributions: each team's scores are modeled as normally distributed about its season mean, so the probability that a team wins is the normal probability that its score exceeds its opponent's given the two means and standard deviations. A team's standard deviation SHALL be its own scoring standard deviation when it has at least three played games and a non-trivial spread, and otherwise a league-wide standard deviation; when a team has no played games (or no scoring history is available), the matchup SHALL fall back to an equal 50/50 weight. Points-for SHALL NOT be simulated (it stays fixed and only breaks ties), and the odds SHALL be conditional on the user's current picks — a picked matchup is locked to its picked result and only unpicked matchups vary. The odds SHALL be computed exactly by enumerating all outcome combinations, each weighted by its probability, when the number of unpicked matchups is small enough, and by sampling outcomes at their win probabilities otherwise.

#### Scenario: Odds in the base view
- **WHEN** the standings table is shown with no picks made
- **THEN** each team's row shows a playoff-odds percentage computed over all possible results of the remaining matchups

#### Scenario: Stronger-scoring team is favored
- **WHEN** exactly one regular-season matchup decides a seat between two teams whose records leave the seat open, and one team's regular-season scoring distribution is clearly stronger than the other's
- **THEN** the stronger-scoring team shows more than 50% and the weaker one less than 50%, rather than an even split

#### Scenario: Equal-weight coin-flip outcomes
- **WHEN** exactly one regular-season matchup remains between two teams that are otherwise tied on record and points-for and no regular-season games have been played to establish scoring distributions
- **THEN** the matchup is treated as an equal 50/50 outcome and each of those two teams shows 50% playoff odds

#### Scenario: Odds are conditional on picks
- **WHEN** the user picks a winner for a remaining matchup
- **THEN** that result is locked in and the playoff-odds column recomputes over only the still-unpicked matchups

#### Scenario: Clinched and eliminated extremes
- **WHEN** a team is in a top-`num_playoff_teams` seed regardless of any remaining result, or cannot reach one under any remaining result
- **THEN** its playoff odds read 100% or 0% respectively

#### Scenario: Large outcome space is sampled
- **WHEN** the number of unpicked matchups is too large to enumerate every combination
- **THEN** the playoff odds are estimated by sampling possible outcomes at their win probabilities rather than left unshown

### Requirement: Show per-team playoff seed probabilities
The projected-standings table SHALL include, for each team, one column per playoff seed `1..num_playoff_teams`, each cell showing the share of possible remaining outcomes in which that team finishes in that exact seed. For each team, these per-seed probabilities SHALL sum to its playoff-odds percentage (its chance of finishing in a top-`num_playoff_teams` seed), so no separate "miss the playoffs" column is shown. The probabilities SHALL be computed over the same weighted enumeration of remaining outcomes as the playoff odds — each un-picked matchup weighted by the probability that each team wins it, derived from the two teams' regular-season scoring distributions and falling back to an equal 50/50 weight when a team has no scoring history, with points-for fixed and used only to break ties — and SHALL be conditional on the user's current picks. They SHALL be computed exactly by enumerating all outcome combinations when the number of un-picked matchups is small enough, and by sampling outcomes otherwise. The per-seed columns SHALL be shown in both the live in-progress tool and the demo replay.

#### Scenario: Seed distribution per team
- **WHEN** the projected-standings table is shown
- **THEN** each team's row shows, for every seed `1..num_playoff_teams`, the probability of finishing in that seed across the remaining outcomes, and those probabilities sum to the team's playoff-odds percentage

#### Scenario: Conditional on picks
- **WHEN** the user picks a winner for a remaining matchup
- **THEN** that result is locked in and the seed probabilities recompute over only the still-unpicked matchups

#### Scenario: Consistent with the playoff-odds column
- **WHEN** a team's seed probabilities and its playoff-odds percentage are both shown
- **THEN** the sum of the team's probabilities for seeds `1..num_playoff_teams` equals its playoff-odds percentage

#### Scenario: Large outcome space is sampled
- **WHEN** the number of unpicked matchups is too large to enumerate every combination
- **THEN** the seed probabilities are estimated by sampling possible outcomes at their win probabilities rather than left unshown

#### Scenario: Shown in demo replay
- **WHEN** the predictor runs in replay mode over a completed season
- **THEN** the per-seed columns are shown for that season's teams
