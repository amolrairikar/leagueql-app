# Design

## Endpoint choice per data type

`_build_all_request_urls` picks the base URL per `(season, data_type)` instead of per season.
`leagueHistory` is used when `season <= V2_CUTOFF`, except for `matchups` in seasons
`>= ESPN_BOXSCORE_SEASONS_ENDPOINT_FROM` (2018), which use the seasons endpoint.

## Why not lower `V2_CUTOFF` to 2017

`V2_CUTOFF` also selects how `_filter_player_scoring_totals` reads a player's season total
(`stats[0].appliedTotal` vs `ratings["0"].totalRating`). The other 2018 data types work today,
so moving the whole season would change parsing that is not broken. Only the matchup fetch moves.

## Seasons before 2018

Not changed. It is unverified whether ESPN serves box scores for them on either endpoint.

## Response shape

The seasons endpoint returns an object, not a single-element list. `_unwrap` already handles
both, and `_filter_matchups` only reads `schedule`.
