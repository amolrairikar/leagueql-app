# BE-004: Data Processing Pipeline (Precomputed Views)

## Description
Transforms raw platform API payloads (stored in S3) into precomputed, query-ready views
written to DynamoDB. Runs in the processor Lambda using DuckDB to execute per-platform SQL
transforms. Each view is written under the league's canonical partition key with an
entity-specific sort key. This pipeline backs every read feature in the app — the frontend
only ever reads these precomputed items via [BE-005](BE-005-query-precomputed-views-api.md).

## Scope
- Processor Lambda: `src/processor/` (`handler.py`, `queries.py`, `utils.py`).
- SQL transforms: `src/processor/queries.py` (`QUERIES`, keyed by entity type and platform).
- Entity types (`EntityType`): `TEAMS`, `MATCHUPS`, `STANDINGS`, `WEEKLY_STANDINGS`,
  `PLAYOFF_BRACKET`, `DRAFT`, `TRANSACTIONS` (Sleeper-only; see
  [BE-019](BE-019-sleeper-transactions.md)).
- Output schema: `docs/db/dynamodb_spec.md`.

## Computed Views
- **TEAMS** (`TEAMS`): all teams across all seasons (owner, team name/logo, owner IDs).
- **MATCHUPS** (`MATCHUPS#{season}#WEEK#{week}`): per-week matchups with starters/bench,
  scores, winner/loser, playoff tier/round.
- **STANDINGS** (`STANDINGS#{season}`): per-season standings including record, win%,
  vs-league record, points for/against.
- **WEEKLY_STANDINGS** (`WEEKLY_STANDINGS#{season}`): cumulative standings snapshot per
  team per regular-season week.
- **PLAYOFF_BRACKET** (`PLAYOFF_BRACKET#{season}`): bracket structure with seeding refs
  (`team_*_from`), placement positions, winners/losers.
- **DRAFT** (`DRAFT#{season}`): every pick with computed analytics — `drafted_position_rank`,
  `actual_position_rank`, `draft_rank_delta`, `vorp`, plus keeper/auction fields.
- **TRANSACTIONS** (`TRANSACTIONS#{season}`): Sleeper-only; completed waivers, trades, and
  free-agent moves with player names and team labels resolved. See
  [BE-019](BE-019-sleeper-transactions.md).

## Edge Cases
- **Platform-specific schemas:** ESPN and Sleeper raw payloads differ; transforms are
  selected per platform. Position ID mappings differ (`ESPN_POSITION_ID_MAPPING`, etc.).
- **Auction drafts:** populate `bid_amount`, `nominating_team_id`; null for snake.
- **Keepers:** `keeper` / `reserved_for_keeper` handled; `reserved_for_keeper` null for Sleeper.
- **VORP undefined for K and D/ST:** `vorp` is null for those positions.
- **Missing player metadata/stats:** `player_name`, `total_points`, `position` may be null;
  views must still write without erroring.
- **Empty/absent Sleeper playoff bracket:** a season whose `playoff_bracket`/`losers_bracket`
  raw data is an empty list (or missing entirely — see the null-bracket edge case in
  [BE-001](BE-001-league-onboarding.md)) produces no `PLAYOFF_BRACKET#{season}` item; the
  processor tolerates this without erroring rather than assuming every season has a bracket.
  Its matchups in the "typical playoff weeks" (week `>= playoff_week_start`) are classified as
  `playoff_tier_type = NONE` (regular season) rather than defaulting to `LOSERS_BRACKET`: with
  no bracket there is no way to identify which games are playoff games. The `LOSERS_BRACKET`
  fallback for a game not found in the bracket applies only when the season *has* a bracket
  (an uncaptured consolation game).
- **Partial Sleeper winners-bracket `from` links:** some Sleeper leagues populate `t1_from`/
  `t2_from` only on the final round, leaving earlier rounds with concrete roster IDs and no
  feeder links. The processor reconstructs the missing links from round + winner/loser
  membership (matching each team to the prior-round game it came from), so the championship
  path — and therefore the `WINNERS_BRACKET` vs. `WINNERS_CONSOLATION_LADDER` tiering — is
  identified correctly instead of stopping one round short and mislabelling early-round games
  as consolation. Links Sleeper already provided are preserved; a bye team (no prior-round
  game) keeps a null `from` so [FE-008](../frontend/FE-008-playoff-bracket.md) still renders
  its bye card.
- **Co-owned teams:** `secondary_owner_id` populated when present, else null.
- **Migrated leagues:** owner IDs must be resolved across platforms via the
  `PLATFORM_MIGRATION` mapping so all-time aggregates stay continuous.
- **Bench slot detection (Sleeper):** `BN`, `IL`, `IR`, `TAXI` are bench slots.
- **Starter slot labels:** each starter's `fantasy_position` reflects the actual lineup
  slot it filled. Sleeper derives this from the league's `roster_positions` (positionally,
  bench slots removed). ESPN derives it from each player's `lineupSlotId` via
  `ESPN_FANTASY_POSITION_ID_MAPPING`, which covers all starting slots (Superflex/`OP`,
  two-QB/`TQB`, the `RB/WR` and `WR/TE` flex variants, IDP, `P`, `HC`); only slots outside
  that set fall back to `FLEX`. Non-standard formats are therefore labelled accurately
  rather than collapsing every non-PPR-offense slot to `FLEX`.
- **Large leagues:** processor runs up to ~120s; writes parallelized across views.
- **Refresh:** views are overwritten in place (idempotent per `(canonical_league_id, SK)`).
- **Season selection / `reprocess_all`:** a normal refresh recomputes only the latest
  season (`resolve_seasons_to_process`). When the manifest carries the `reprocess_all=true`
  metadata flag (set by the BE-019 backfill re-onboard), the processor recomputes **every**
  season in the manifest from the raw season files already in S3 instead.

## Acceptance Criteria
- [ ] For each onboarded season, the processor writes `TEAMS`, `MATCHUPS#{season}#WEEK#{week}`,
      `STANDINGS#{season}`, `WEEKLY_STANDINGS#{season}`, `PLAYOFF_BRACKET#{season}`, and
      `DRAFT#{season}` items matching the schema in `docs/db/dynamodb_spec.md`. A season with an
      empty/absent Sleeper bracket writes no `PLAYOFF_BRACKET#{season}` item and does not error.
- [ ] ESPN and Sleeper inputs produce views with identical schemas (platform differences
      normalized).
- [ ] Draft analytics (`drafted_position_rank`, `actual_position_rank`, `draft_rank_delta`,
      `vorp`) are computed; `vorp` is null for K and D/ST.
- [ ] On refresh, existing view items are overwritten rather than duplicated.
- [ ] A processing failure writes a `FAILED` job status and does not leave partially-valid
      `METADATA` marked as completed.
- [ ] Any change to a precomputed view's schema is reflected in `docs/db/dynamodb_spec.md`
      in the same change.

## Sources
`src/processor/queries.py`, `src/processor/handler.py`, `docs/db/dynamodb_spec.md`.
