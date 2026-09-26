# playoff-race-predictor Specification

## Purpose

The playoff-race predictor lets a manager pick the winners of the remaining regular-season matchups and watch a projected standings table re-sort live around the playoff cutoff, turning the pre-playoff Playoff Bracket page into an interactive "who makes it" tool.

## Requirements

### Requirement: Pick winners of remaining regular-season matchups
The predictor SHALL let the user select a winner for each pickable matchup by clicking a team, SHALL let the user clear that pick by clicking the selected winner again, and SHALL provide a control that resets all picks. Matchups left unpicked SHALL NOT affect the projection.

#### Scenario: Pick a winner
- **WHEN** the user clicks a team in a pickable matchup
- **THEN** that team is marked the winner and the projected standings update to include the result

#### Scenario: Unpick by reclicking
- **WHEN** the user clicks a team that is already the selected winner of its matchup
- **THEN** the pick is cleared and the projected standings revert that matchup's effect

#### Scenario: Reset all picks
- **WHEN** the user activates the reset control
- **THEN** every pick is cleared and the standings return to the baseline (records through the last completed regular-season week)

### Requirement: Project standings live from picks
The predictor SHALL render a standings table ordered by projected wins descending, then points-for descending, that updates whenever a pick changes. Points-for SHALL be the season-to-date total used only as a tiebreaker.

#### Scenario: Standings re-sort on a pick
- **WHEN** a pick changes a team's projected record enough to change the order
- **THEN** the standings table re-sorts to reflect projected wins (ties broken by points-for)

#### Scenario: Movement versus current standings
- **WHEN** a team's projected seed differs from its baseline seed
- **THEN** the row shows an up/down movement indicator of the seed change

### Requirement: Show the playoff cutoff line
The standings table SHALL draw a cutoff line after the league's configured number of playoff teams, visually distinguishing seeds that would make the playoffs. When the playoff-team count was not provided by the platform and a default was used, the cutoff SHALL be labeled as assumed.

#### Scenario: Cutoff at configured count
- **WHEN** the league settings report `num_playoff_teams`
- **THEN** the cutoff line is drawn after that many seeds and those seeds are marked as making the playoffs

#### Scenario: Assumed cutoff note
- **WHEN** the playoff-team count was defaulted (platform omitted it)
- **THEN** the cutoff is labeled to indicate the count is assumed

#### Scenario: Clinched seed
- **WHEN** a team has secured a top-`num_playoff_teams` seed by wins alone regardless of any remaining pick
- **THEN** its row shows a clinched indicator

### Requirement: Show each team's record entering the week
Each team card in a matchup SHALL display the team's record entering that week — its baseline record plus the results of the user's picks in earlier weeks only. A pick in the current week SHALL NOT change the record shown on that same card.

#### Scenario: Record reflects earlier-week picks
- **WHEN** the user picks winners in an earlier week and advances to a later week
- **THEN** the later week's team cards show records that include those earlier picks

### Requirement: Step through remaining weeks one at a time
The predictor SHALL present the pickable matchups grouped by week and let the user move between weeks one at a time, showing for each week how many of its matchups have been picked.

#### Scenario: Week navigation
- **WHEN** the user moves to another remaining week
- **THEN** only that week's matchups are shown, with an indication of how many are picked

### Requirement: Only remaining regular-season matchups are pickable
The predictor SHALL only make regular-season matchups within the league's regular season (week ≤ `regular_season_weeks`) pickable; playoff matchups and weeks after the regular season SHALL NOT be pickable. In a live in-progress season the pickable set is the unplayed regular-season weeks; in a demo replay it is the last three regular-season weeks presented unpicked.

#### Scenario: Live in-progress season
- **WHEN** the predictor runs for an in-progress season
- **THEN** the pickable matchups are the unplayed (both scores `0`) regular-season matchups bounded by `regular_season_weeks`

#### Scenario: Playoff weeks excluded
- **WHEN** the matchup data includes weeks at or after the playoff start
- **THEN** those weeks are never pickable and never contribute to the projected regular-season standings

#### Scenario: Demo replay
- **WHEN** the predictor runs in replay mode over a completed season
- **THEN** it presents the last three regular-season weeks as pickable (unpicked) with the baseline being records entering that window

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

### Requirement: Surface playoff clinching scenarios
Below the projected-standings table, the predictor SHALL surface a clinching-scenarios section that lists only teams still in playoff contention whose next un-picked game is decisive: winning it makes the team finish in a top-`num_playoff_teams` seed in every remaining outcome ("win & in"), losing it makes the team miss in every remaining outcome ("must win"), or both ("controls its own destiny"). Scenarios SHALL be computed exactly over the same enumeration of un-picked outcomes as the playoff odds and SHALL be conditional on the user's picks, treating each team's earliest un-picked matchup as the decisive game. A berth SHALL count as clinched only when record alone secures it; teams already clinched or already eliminated SHALL NOT be listed. When a listed team's seat could come down to a same-record tie, the scenario SHALL state the points-for margin versus the rival(s) it must hold off, because points-for keeps accumulating in the games still to play. The section SHALL appear only when the number of un-picked matchups is small enough to enumerate exactly and at least one team qualifies.

#### Scenario: Win and in
- **WHEN** a contending team would finish in a top-`num_playoff_teams` seat in every remaining outcome in which it wins its next un-picked game
- **THEN** the section lists it as "win & in" for that game

#### Scenario: Must win
- **WHEN** a contending team would miss a top-`num_playoff_teams` seat in every remaining outcome in which it loses its next un-picked game
- **THEN** the section lists it as "must win" that game

#### Scenario: Controls its own destiny
- **WHEN** a team both clinches with a win and is eliminated with a loss in its next un-picked game
- **THEN** the section lists it as controlling its own destiny (win to clinch, out with a loss)

#### Scenario: Clinched and eliminated teams are excluded
- **WHEN** a team is clinched by record alone, or eliminated under every remaining outcome
- **THEN** it is not listed in the clinching-scenarios section (its status is shown in the standings)

#### Scenario: Same-record tie margin
- **WHEN** a listed team's seat in some remaining outcome comes down to a same-record tie with one or more rivals
- **THEN** the scenario states the points-for margin (the current points-for gap) versus each such rival that the team must hold off

#### Scenario: Conditional on picks
- **WHEN** the user picks a winner for a remaining matchup
- **THEN** the clinching scenarios recompute over only the still-unpicked matchups

#### Scenario: Hidden when nothing is decisive
- **WHEN** no contending team's next game is decisive, or the un-picked outcome space is too large to enumerate exactly
- **THEN** the clinching-scenarios section is not shown

#### Scenario: Odds versus scenarios note
- **WHEN** the clinching-scenarios section is shown alongside the playoff-odds column
- **THEN** a note distinguishes the odds (how likely a team is to make it) from the scenarios (what is mathematically guaranteed or required), and notes that same-record ties are decided by points-for including points still to be scored

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
