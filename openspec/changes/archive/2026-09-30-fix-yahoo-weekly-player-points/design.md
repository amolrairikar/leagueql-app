# Design

## Context

We compared raw Yahoo responses for week 2 of league 1676376:
- `league/{key}/teams/roster;week=W/players/stats;type=week;week=W` returns roster metadata only,
  with no `player_points` or `player_stats`.
- `team/{team_key}/roster;week=W/players/stats;type=week;week=W` returns
  `player_points.total` for every player.

The existing player parsing reads the single-team shape correctly. Only the top-level container
differs: `fantasy_content.team` instead of `fantasy_content.league[1].teams`.

## Decisions

- **Per-team roster URLs, built up front.** Yahoo team keys are always
  `{league_key}.t.1 … .t.{num_teams}`, and `num_teams` is in the league metadata that season
  resolution already reads. That lets the URLs be built without first waiting for the `teams`
  call.
- **Merge back to `rosters_week{W}`.** Each per-team fetch uses the data type
  `rosters_week{W}_t{t}`. After filtering, the results for a season/week are merged into one
  `rosters_week{W}` record. The raw-data shape stored in S3 and read by the processor stays the
  same, so the processor doesn't change.
- **Season resilience is unchanged.** A failed per-team roster fetch counts as a failed fetch for
  its season, so `validate_api_results` drops the season, the same as any other failed call.
- **Missing team count.** If `num_teams` is missing or 0, log a warning and skip that season's
  roster URLs. Matchups still load, with empty lineups.

## Alternatives considered

- **Batched weekly player stats** (`league/{key}/players;player_keys=…/stats;type=week;week=W`)
  keyed off the league-wide roster call. It makes a similar number of calls, but it has to run
  after the roster call and needs a join. We rejected it because it's more complex.
