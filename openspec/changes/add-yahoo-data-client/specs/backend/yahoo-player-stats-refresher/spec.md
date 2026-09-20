## Purpose
Scheduled ECS Fargate task that fetches Yahoo NFL player metadata (name, position) and per-player
season fantasy scoring across the player pool, using a dedicated service Yahoo credential, and
caches them in S3 where the processing pipeline reads them to resolve Yahoo player names/positions
and compute draft analytics (`total_points`, `actual_position_rank`, `draft_rank_delta`, `vorp`).
Runs as a Fargate task (no 15-minute Lambda cap) on a schedule, paced to stay within Yahoo's API
limits.

## ADDED Requirements

### Requirement: Use a dedicated service Yahoo credential
The refresher SHALL authenticate to the Yahoo API using a configured service account's stored
Yahoo OAuth token, obtaining and refreshing the access token through the shared token engine, and
SHALL NOT use any onboarding user's token. The service account's Clerk user id and its service
league key SHALL be resolved at runtime from SSM parameters named by the
`YAHOO_SERVICE_USER_ID_SSM_PARAM` and `YAHOO_SERVICE_LEAGUE_KEY_SSM_PARAM` env vars, so the values
never land in Terraform state or CI and can be re-pointed without a redeploy.

#### Scenario: Service token used and refreshed
- **WHEN** the refresher runs
- **THEN** it resolves the service account id from its SSM parameter, obtains a valid access token
  for that account (refreshing if near expiry), and uses it as the Bearer credential for all Yahoo
  requests

#### Scenario: Service account not configured
- **WHEN** either service SSM parameter is unset or resolves to an empty value
- **THEN** the run fails fast with a clear configuration error and writes no partial cache

#### Scenario: Service link missing or revoked
- **WHEN** the service account has no Yahoo link or its refresh token is revoked
- **THEN** the run fails with a clear re-link error and writes no partial cache

### Requirement: Refresh player metadata and season stats
On a successful run the refresher SHALL write current NFL player metadata (name, position) to
`player-metadata/yahoo_nfl_players.json` and per-player season scoring to
`player-stats/yahoo_nfl_player_stats.json`, keyed by Yahoo `player_key`.

#### Scenario: Successful run
- **WHEN** the refresher runs successfully for a season
- **THEN** the S3 metadata cache maps `player_key` → name/position and the stats cache maps
  `player_key` → `{season: total_points}` for the available players

#### Scenario: Pipeline can resolve names and compute analytics
- **WHEN** the processing pipeline reads the Yahoo metadata and stats caches
- **THEN** it can resolve draft/transaction player names/positions and compute `total_points`,
  `vorp`, and position ranks for Yahoo drafts

### Requirement: Deep-merge partial refreshes
A refresh SHALL read the existing stats cache and deep-merge the freshly fetched
`{player_key: {season: stats}}` rather than overwriting, and SHALL bootstrap from empty when no
cache exists.

#### Scenario: Merge preserves other seasons and players
- **WHEN** a refresh fetches a single season
- **THEN** previously cached seasons for the same player and players absent from this run are
  preserved

#### Scenario: No existing cache
- **WHEN** the output object does not exist (`NoSuchKey`/`404`)
- **THEN** the run starts from an empty map and writes the fetched stats

### Requirement: Resilient, rate-limited, paginated fan-out
The refresher SHALL page the Yahoo player collection (25 per page via `start=`), pace requests
under Yahoo's rate limit, and skip individual page/player failures without aborting the run.

#### Scenario: Pagination
- **WHEN** fetching the player pool
- **THEN** it advances `start` by the page size until the collection is exhausted

#### Scenario: Rate limiting and partial failure
- **WHEN** issuing many paged requests and one page fails transiently
- **THEN** requests are paced to avoid throttling and a single failed page is retried/skipped
  without aborting the whole run

### Requirement: Override env vars for test/on-demand runs
The refresher SHALL support `SEASON`, `MAX_PLAYERS`, and `OUTPUT_KEY` overrides for on-demand and
integration-test runs while retaining full production behavior when none are set.

#### Scenario: Bounded test run
- **WHEN** `MAX_PLAYERS` and `OUTPUT_KEY` are set
- **THEN** only the first N players are processed and results are written to the override key,
  exercising the full S3-read → live-fetch → S3-write path while leaving the production cache
  untouched
