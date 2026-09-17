## Context

See proposal.md — Why. Yahoo OAuth linking already exists (`src/api/yahoo_oauth.py`:
authorize/callback, PKCE, KMS-encrypted tokens keyed `USER#{clerk_user_id}` / `YAHOO_OAUTH`,
`get_valid_access_token` with transparent refresh). ESPN/Sleeper onboarding runs through a
duck-typed client contract (`get_seasons()` + `async fetch_all() -> [{"season","data_type","data"}]`)
built by `OnboardingService._build_client`; the onboarder writes raw JSON + `manifest.json` to S3,
which triggers the processor's per-platform DuckDB transforms (`register_raw_data` +
`QUERIES[entity][platform]`). Yahoo must slot into that contract without new pipeline stages.

Key Yahoo API constraints:
- Base `https://fantasysports.yahooapis.com/fantasy/v2`, JSON via `?format=json` (Yahoo JSON uses
  numeric-keyed objects and mixed count/array shapes — normalization is the bulk of the work).
- A league is addressed by a season-specific `league_key = {game_key}.l.{league_id}`; Yahoo issues
  a new numeric `league_id` each season, linking seasons via a `renew` pointer in league metadata.
- Access tokens live ~1 hour — shorter than a full multi-season historical onboard.

## Goals / Non-Goals

**Goals:**
- A `YahooClient` that mirrors the ESPN/Sleeper contract and yields the same grouped views the
  processor already consumes.
- The onboarder can obtain and refresh Yahoo tokens for the whole run.
- Yahoo transforms produce byte-for-byte-compatible view schemas (no frontend/query changes).

**Non-Goals:**
- Live-API integration tests (deferred; needs a real linked test account).
- Any change to the OAuth linking round-trip itself.

## Decisions

**1. League + history resolution via the logged-in user, then the renew chain.**
`get_seasons()` (sync, like ESPN's resolver) calls `GET /users;use_login=1/games;game_codes=nfl/leagues`.
This simultaneously (a) verifies the owner belongs to the entered league (authz), (b) resolves the
numeric `league_id` → current `league_key`, and (c) yields the seasons the user has. It then walks
each league's `renew` pointer to assemble the full lineage's season→`league_key` map under one
canonical league. Alternative — construct `league_key` directly from a game-key table — rejected:
it can't verify membership and hard-codes season→game_key mappings.

**2. Onboarder self-refreshes tokens via a shared module (not a token passed in the invoke).**
Extract token get/refresh/decrypt from `src/api/yahoo_oauth.py` into `src/common/yahoo_tokens.py`;
`yahoo_oauth.py` re-imports it so the API surface is unchanged. The onboarder imports the shared
module and refreshes on demand during `fetch_all`. Alternative — API pre-fetches a token and passes
it in the invoke body — rejected: a historical onboard can outlast the ~1 hr token, and there's no
way to refresh a token that lives only in the event payload.

**3. Reuse the existing async fetch helpers with a Bearer header + pagination.**
`fetch_all` uses `run_fetches`/`fetch_with_retry` (`src/onboarder/utils.py`) with
`Authorization: Bearer`. Weeks come from Yahoo `settings` (`start_week`..`end_week`,
`playoff_start_week`), not the ESPN/Sleeper `matchup_weeks()` heuristic. `players`/`transactions`
are paginated with `start=`. Concurrency is kept conservative to respect Yahoo rate limits.

**4. Derive the playoff bracket from playoff-week matchups (ESPN model).**
Yahoo exposes no bracket resource, so `_build_yahoo_brackets` infers rounds/tiering from
scoreboard matchups flagged `is_playoffs`, exactly as ESPN's `_build_espn_brackets` does — keeping
`PLAYOFF_BRACKET` schema parity.

**5. Per-type filter functions normalize Yahoo JSON at the client boundary.**
Like `_ESPN_DATA_FILTERS`, Yahoo filters flatten Yahoo's numeric-keyed JSON into the plain dict
shapes `_register_yahoo_raw_data` expects, so processor SQL stays close to the ESPN transforms.
The response shapes are translated from the XML examples in Yahoo's resource docs; normalization
is isolated in filter functions and covered by canned-JSON fixtures, with the DEV integration run
as the real-data check.

**5b. Player names + season points come from a separate Yahoo player-data pipeline, not the
per-league onboard.** Yahoo has no cheap "season totals for a league's rostered players" call —
season stats require paginating the player pool with league scoring applied, which is far too
heavy to run inside every onboard. So, mirroring Sleeper (`sleeper_player_stats_refresher` +
`player_metadata`), a **dedicated Yahoo player-data ECS task** (Dockerfile + `main()`) periodically
fetches `players;out=metadata,stats` across the pool and writes `player-metadata/yahoo_nfl_players.json`
and `player-stats/yahoo_nfl_player_stats.json` to S3; the processor reads those (as it already does
for Sleeper) to resolve draft/transaction player names/positions and draft VORP. The onboarder's
`YahooClient` therefore fetches only per-league data (settings/standings/teams/matchups/
draftresults/transactions) and carries player *keys*, not names. Alternatives — targeted
per-league batch fetch by player_key, or aggregating weekly matchup rosters — were rejected as
incomplete for VORP and as coupling heavy stat fetching to the latency-sensitive onboard path.

**5c. The player-data task uses a dedicated service Yahoo credential, not any onboarding user's
token.** The service account (the maintainer's own Yahoo account) is linked once through the normal
OAuth flow; its token item (`USER#{id} / YAHOO_OAUTH`) is addressed by a configured
`YAHOO_SERVICE_USER_ID`, and the task obtains/refreshes access through the shared
`common/yahoo_tokens` engine. This reuses the existing storage + refresh path rather than
introducing a separate secret-provisioning mechanism. Alternative — a raw refresh token in SSM —
rejected: it would duplicate the encrypt/refresh logic the token module already owns.

**6. Cross-region KMS for decrypt in the onboarder.**
The Yahoo KMS key is pinned to `YAHOO_KMS_REGION` (us-east-1). The shared module builds its own KMS
client in that region so decrypt works regardless of the onboarder Lambda's region; the onboarder
role gains `kms:Decrypt` on that key + SSM read for the client id (deferred OAuth task 7.2).

## Risks / Trade-offs

- **Yahoo JSON is awkward and under-documented** → model canned real responses in unit fixtures;
  keep normalization isolated in filter functions so shape surprises are localized.
- **Rate limiting on many per-week/paginated calls** → conservative concurrency + existing
  exponential-backoff retry; matchup weeks bounded by settings rather than a fixed 18.
- **Token revoked mid-run** → surface as a `FAILED` job with `YAHOO_AUTH` so the UI prompts a
  reconnect (spec'd in league-onboarding).
- **Refactor risk extracting the token module** → `yahoo_oauth.py` re-exports the moved names and
  its existing unit tests (relocated) guard behavior parity.
- **Sequencing** → this change's frontend/OAuth deltas reference specs that live in the not-yet-
  archived `add-yahoo-league-support` change; archive it first (task 1) so the base specs are live.

## Migration Plan

1. Archive `add-yahoo-league-support` so `backend/yahoo-oauth` + `frontend/connect-yahoo-league`
   become live base specs.
2. Ship backend (token module + client + processor) with tests; deploy onboarder IAM/env
   (KMS/SSM) **before** enabling the real onboard path.
3. Flip the `routes.py` gate to the real invoke; ship frontend polling.
4. Rollback: revert the `routes.py` gate to the "coming soon" response — the client/transform code
   is dormant until the gate invokes it.
