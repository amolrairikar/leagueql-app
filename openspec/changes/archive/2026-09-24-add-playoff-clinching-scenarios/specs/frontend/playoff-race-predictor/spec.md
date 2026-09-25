## ADDED Requirements

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
