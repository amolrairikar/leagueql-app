## ADDED Requirements

### Requirement: Plot in-progress seasons at their current standings position

The "Final standings position by season" chart SHALL plot an in-progress season — one
where no team has a finalized placement (`final_rank` is `0`, as ESPN reports
`rankCalculatedFinal` before a season is finalized, or absent) yet at least one game has
been played — at each owner's current standings position, derived from the
regular-season record ordered by wins then points-for, rather than plotting rank `0`. A
season with no games played yet SHALL plot no point.

#### Scenario: In-progress season plotted at current standings position

- **WHEN** the `SEASON_STANDINGS#` data includes an in-progress season whose rows carry
  `final_rank: 0` and at least one played game
- **THEN** the standings-position chart plots each owner at their current standings
  position (ordered by wins, then points-for) for that season — never a rank-`0` point
