## Context

See proposal.md — Why. Transactions are already a full Sleeper-only pipeline: per-week fetch →
`compile_sleeper_transactions` → DuckDB `transactions` view → chunked `TRANSACTIONS#{season}`
DynamoDB items → `queryType=TRANSACTIONS#{season}` → Sleeper-gated `/transactions` page. The row
shape (`season, transaction_id, type, week, created, roster_ids, teams, adds, drops, draft_picks,
waiver_bid`) and its empty-view guard (`_EMPTY_VIEW_DTYPES["transactions"]`) are platform-agnostic
already. This change adds an ESPN producer that emits the same rows.

ESPN transaction data comes from `...?view=mTransactions2`, whose `transactions[]` array is
returned whole for a season in one call (no per-week paging). Only the current season returns data.

## Goals / Non-Goals

**Goals:**
- Reuse the existing `transactions` view, chunking, `EntityType.TRANSACTIONS`, query API, and
  frontend `TransactionItem` type unchanged — ESPN only adds a new compile path and un-gates the UI.
- Keep raw S3 payloads lean by trimming transactions in the ESPN client filter (as other ESPN
  filters do).

**Non-Goals:**
- Trades (multi-team TRADE items) and ROSTER lineup moves — deferred.
- A scheduled ESPN refresh or a backfill of existing leagues — ESPN has no nightly refresh; leagues
  populate transactions on their next manual onboard/refresh.
- Changing the trade rest-of-season-points UI logic — ESPN produces no `trade` rows, so that path
  is simply never exercised.

## Decisions

- **Current-season-only fetch, single call.** In `_build_all_request_urls`, emit the transactions
  URL only for `max(int(s) for s in self.seasons)`. Alternative (fetch every season) rejected: past
  ESPN seasons return no transaction data, so it would be wasted calls. Unlike `matchups`, no
  per-week expansion — `mTransactions2` returns the whole season at once.
- **Filter in the client, compile in the processor.** `_filter_transactions` keeps only `EXECUTED`
  `FREEAGENT`/`WAIVER` records and trims each to the needed fields before S3 (mirrors the other ESPN
  filters). `compile_espn_transactions` in the processor produces the shared row shape. This matches
  the Sleeper split (filter-ish upstream, compile in `_register_*`).
- **Resolve players from `player_scoring_totals`.** The `kona_player_info` view already fetched for
  scoring gives a `player_id → {name, position}` map for the season; reuse it rather than adding
  another ESPN player-info call. Teams resolve from `mTeam` members/teams via the same
  `primaryOwner → member` join the ESPN TEAMS query uses. New helper `build_espn_team_map` mirrors
  `build_sleeper_roster_team_map`.
- **Relax the write guard, not duplicate it.** Change the schema-build guard from
  `platform == "SLEEPER" and grouped.get("transactions")` to just `grouped.get("transactions")`; the
  compile step is what's platform-specific, so the write path stays single.
- **Platform-aware UI, minimal branch.** The frontend keeps one page; only the filter list/default
  and the summary Trades column branch on platform. ESPN defaults to Free Agents so the first render
  is never an always-empty Trades view.

## Risks / Trade-offs

- **Deep-bench players may not resolve to a name** → `kona_player_info` returns roughly the top 1500
  players by applied stat total, so an add/drop of a very low-owned player can resolve to
  `player_name = null`. Mitigation: graceful fallback (`Player {id}` in the UI), matching the
  existing Sleeper "unknown player" behavior; acceptable and non-fatal.
- **ESPN league-history endpoint lacks `mTransactions2`** → only the modern
  `seasons/.../leagues/...` endpoint supports it. Mitigation: we only ever request the current
  season, which is always post-2018 / v2, so the legacy endpoint is never used for transactions.
- **Selecting a past ESPN season shows an empty page** → only the current season has data.
  Mitigation: the existing 404-→-empty-state path already handles this gracefully; the season
  selector still lists all seasons for consistency with other pages.
- **Existing ESPN leagues show nothing until re-onboarded/refreshed** → no nightly ESPN refresh
  exists. Accepted as a follow-up (a one-off backfill would need to re-fetch, not just reprocess).
