# Design

## Reuse the REFRESH path and change only the season list

Each platform client already takes an `is_refresh` flag that limits fetching to the latest
season. When `is_refresh=False`, the client resolves the full history: ESPN's `previousSeasons`
plus the latest season, the whole Sleeper `previous_league_id` chain, and the whole Yahoo
`renew` chain. A refetch-all REFRESH builds the client with `is_refresh=False` and keeps
everything else on the REFRESH path:

- **Writer:** the REFRESH branch updates `LEAGUE_LOOKUP` with `ADD seasons` and leaves the owner
  and members on METADATA untouched.
- **S3:** `upload_results_to_s3` overwrites `{season}.json` for each fetched season and merges
  the manifest's season list.
- **Yahoo:** `_lineup_pending_seasons` already marks every onboarded season as lineup-pending, so
  each re-fetched season is queued for the lineup backfill again.

## `LEAGUE_LOOKUP` seasons

For Sleeper, the latest season's lookup item receives every historical season, even though
older seasons also have their own lookup items. No deduplication is needed:

- `seasons` is a string set, so `ADD` ignores values already present.
- `get_league_seasons` takes the union across lookup items.
- The scheduled refresh and the backfill script read only `max(seasons)`.
- A first ONBOARD already writes the full season list onto one lookup item.

## `refetchAll` implies `reprocess_all`

Without `reprocess_all`, the processor rebuilds only the latest season, so re-fetched historical
data would never reach the views. The handler sets
`reprocess_all = reprocessAll or refetch_all`.

## Scope: REFRESH only

The handler accepts `refetchAll` only when the request type (after Sleeper renewal resolution)
is `REFRESH`. An ONBOARD already fetches every season, and MIGRATE semantics stay unchanged.
