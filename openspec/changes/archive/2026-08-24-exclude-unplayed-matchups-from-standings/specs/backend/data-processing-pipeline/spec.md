## ADDED Requirements

### Requirement: Exclude unplayed matchups from standings

The processor SHALL treat a regular-season matchup whose team scores are both exactly `0` as
unplayed and exclude it from the `STANDINGS` and `WEEKLY_STANDINGS` view computations, while still
writing that matchup into the `MATCHUPS#{season}#WEEK#{week}` view. Wins, losses, ties, win
percentage, points for/against (and their averages), games played, and the per-week all-play
("vs league") ranking SHALL reflect only played matchups.

#### Scenario: Unplayed week excluded from standings

- **WHEN** a season contains a regular-season week whose matchups are all `0-0` (unplayed)
- **THEN** `STANDINGS#{season}` and `WEEKLY_STANDINGS#{season}` do not count that week — games
  played, wins/losses/ties, win %, and points for/against are computed from the played weeks only

#### Scenario: Unplayed matchup still stored

- **WHEN** an unplayed `0-0` week is processed
- **THEN** its `MATCHUPS#{season}#WEEK#{week}` item is still written with the `0-0` rows intact

#### Scenario: Genuine played game with a zero score is retained

- **WHEN** a played matchup has one team scoring `0` and the other scoring more than `0`
- **THEN** it is counted in standings as a normal decided game (not excluded)
