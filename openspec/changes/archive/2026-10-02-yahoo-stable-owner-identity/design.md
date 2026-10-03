# Design

## Context

See proposal.md (Why) for the problem. Current state relevant to the approach:

- `resolve_team_owner_ids` (`src/common/yahoo_members.py`) chooses guid-or-`manager_id` for the
  **whole league**. One masked, missing, or duplicate guid makes every team fall back to the slot
  number. It is shared by the onboarder (`_filter_teams` in `src/onboarder/yahoo_client.py`) and
  the members proxy (`parse_managers`).
- The raw teams record stores the resolved id in `manager_id`, so the processor can't tell a
  guid from a slot number. It does keep `nickname`, team `name`, and `logo`, and those are enough
  to link people across seasons.
- The processor (`_process_manifest` in `src/processor/handler.py`) loads only
  `seasons_to_process` from S3. Incremental runs process just the new or latest season (see
  `resolve_seasons_to_process`), and the other seasons' items in DynamoDB are left as they are.
- `_register_yahoo_raw_data` builds ESPN-shaped `members`/`teams` rows (`id`, `primaryOwner`,
  `owners`) that feed the shared TEAMS/MATCHUPS/STANDINGS transforms. Downstream SQL and the
  frontend group cross-season data by `owner_id` = `primaryOwner`.
- `PLATFORM_MIGRATION` stores `newPlatformOwnerId` values that come from the members proxy. The
  frontend remaps source-platform owner ids through it.

## Goals / Non-Goals

**Goals:**
- One `owner_id` per real person across all seasons of a Yahoo league, chosen the same way on
  every run.
- No change to view schemas, the frontend, or the members-proxy response shape.
- Existing raw S3 data is enough. Fixing existing leagues needs only a reprocess, not a re-fetch
  from Yahoo.

**Non-Goals:**
- Manual merge/split of managers by the league owner (a possible follow-up).
- Anchoring the logged-in user via `/users;use_login=1` (a possible follow-up).
- Changing how ESPN/Sleeper owner identity works.

## Decisions

### D1. Per-team guid with masked-value normalization (shared helper)
`resolve_team_owner_ids` treats `--hidden--`, `--`, and empty guids as missing. It then uses
each team's guid only when it is unique within the league, and otherwise that team's
`manager_id`. The members proxy inherits this automatically.
*Alternative:* keep all-or-nothing. Rejected, because one masked manager costs every other team
its real identity.

### D2. Keep `manager_id` as the resolved id; add `guid` and `slot_manager_id`
The raw teams/members rows keep `manager_id` = resolved owner id, so older readers and fixtures
still work. They gain `guid` (the real value or null) and `slot_manager_id` (Yahoo's raw
`manager_id`).
*Alternative:* redefine `manager_id` as the slot only. Rejected, because legacy files would then
be read inconsistently.

### D3. Identity resolution in the processor, not the onboarder
Linking needs every season together. The onboarder fetches one season per refresh, while the
processor already reads raw files from S3. A new pure function
`resolve_yahoo_owner_identities(teams_by_season) -> {(season, team_key): owner_id}` runs inside
`_register_yahoo_raw_data` before member/team rows are built. It rewrites `id`, `primaryOwner`,
and `owners`. `displayName` stays the nickname from that season.

### D4. Matching algorithm
- Walk seasons in ascending order. Each identity accumulates `{guids, nicknames, team_names,
  custom_logos}` from **every** season it has appeared in, so a manager returning after a gap
  is still matched.
- Within a season, run passes in order: guid → nickname → team name → custom logo. In each pass,
  a team links to an identity only when exactly one unclaimed identity matches. A claimed
  identity is unavailable for the rest of that season, so the matching stays one-to-one.
- Normalization:
  - Compare nicknames and team names case-insensitively, after trimming.
  - Never match on nickname `--hidden--`.
  - Never match on a nickname that appears twice within the current season.
  - Exclude Yahoo default logos (URLs containing `/default/` or matching `nfl_<n>.png` /
    `nfl_<n>_d.png`).
- Legacy rows without `guid`: a non-numeric `manager_id` is treated as a guid, and a numeric one as
  a slot.
- *Alternative:* fuzzy matching or similarity scoring. Rejected; exact signals were enough on the
  real data that motivated this change, and wrong merges are worse than missed ones. Missed ones
  can be fixed by a future manual override.

### D5. Stable id = real guid, else the first-season team key
The first-season team key (`<game>.l.<league>.t.<n>`) is globally unique and can't collide with
a guid. It also never changes as later seasons are added, because history doesn't change.
*Alternative:* the id from the person's latest season. Rejected, because every new season could
renumber ids for seasons that were already written, and incremental runs don't rewrite those.

### D6. Load every season's teams record on incremental runs
For YAHOO, the processor also reads `{prefix}/{season}.json` for manifest seasons outside
`seasons_to_process`. It keeps only their `teams` records for identity resolution, and those
seasons' views are not rebuilt. This reuses `read_s3_object` in the existing `ThreadPoolExecutor`.
The extra cost is a few ~200 KB reads per refresh.
*Alternative:* save an identity map (in S3 or DynamoDB). Rejected for now, because it adds a
stateful artifact that can drift. Recomputing gives the same result every time.

### D7. One-time migration-mapping translation
After resolving identities, if `PLATFORM_MIGRATION#<src>#YAHOO` exists without
`yahoo_owner_ids_resolved`:
- Map each `newPlatformOwnerId` to a stable id, matched against the raw owner ids (the
  `manager_id` values) of the **latest** manifest season. On the first processing after a
  migration, that is the season the proxy read.
- Leave `__not_returning__` and unmatched ids unchanged.
- Write the item back with the flag set.

No league has migrated to Yahoo yet, so there are no existing items to convert.

## Risks / Trade-offs

- **[Risk] A false merge:** two different people with the same nickname, team name, or custom
  logo in different seasons. → Mitigation: only unambiguous matches are linked; a duplicate within
  the same season blocks the nickname signal; the stronger signals (guid, nickname) are tried first.
- **[Risk] A missed link:** a manager changes nickname, team name, and logo all at once. → They show
  as two people, the same as some cases today. A manual override would be the follow-up.
- **[Risk] Owner ids change for existing Yahoo leagues.** The Yahoo data is recomputed views, so
  the risk is limited. → Reprocess every Yahoo league after deploy so the ids are consistent across
  seasons. Until a league is reprocessed, its views keep the old ids, which are no worse than today.
- **[Trade-off]** Incremental Yahoo runs read every season file. This is accepted for the
  guarantee of consistency (D6).

## Migration Plan

1. Deploy the onboarder, API (members proxy), and processor together.
2. Run `scripts/utility_scripts/backfill_leagues.py --platform YAHOO` on dev and check one
   league. Then run it on prod with `--execute`. This uses `reprocess_all`, so every season's
   views are rewritten with the new ids.
3. Rollback: redeploy the previous processor and backfill again. The raw data is unchanged
   apart from the added optional fields, which older code ignores.

## Open Questions

None that would change the approach. A manual merge/split override is deferred as a follow-up.
