## 1. Backend — fetch (ESPN client)

- [x] 1.1 Add `"transactions"` to `DATA_FETCH_TYPES` and a `param_map["transactions"] = {"view": ["mTransactions2"]}` entry in `src/onboarder/espn_client.py`; verify a unit test asserts the transactions URL carries `view=mTransactions2`.
- [x] 1.2 In `_build_all_request_urls`, emit the transactions URL only for the latest season (`max(int(s) for s in self.seasons)`), a single call (no per-week loop); verify a unit test with multiple seasons builds exactly one transactions URL, for the latest season only.
- [x] 1.3 Add `_filter_transactions(data, season, data_type)` (register it in `_ESPN_DATA_FILTERS`) that returns `{"transactions": [...]}` keeping only `status == "EXECUTED"` and `type in {"FREEAGENT", "WAIVER"}`, trimmed to `id, type, scoringPeriodId, proposedDate, processDate, bidAmount, teamId, items` (items reduced to `type, playerId, fromTeamId, toTeamId`); verify a unit test drops DRAFT/ROSTER/TRADE_*/non-EXECUTED records and keeps the trimmed fields.

## 2. Backend — compile & store (processor)

- [x] 2.1 Add `build_espn_team_map(all_members, all_teams)` → `season → team_id(str) → {team_name, display_name}` in `src/processor/handler.py`, resolving `team_name` from `teams.name` and `display_name` via `teams.primaryOwner == members.id`; verify a unit test covers resolved and unresolvable teams.
- [x] 2.2 Add `compile_espn_transactions(raw, team_map, player_by_id)` producing the shared transaction row shape (type map FREEAGENT→`free_agent`/WAIVER→`waiver`, `roster_ids=[str(teamId)]`, adds→`toTeamId`, drops→`fromTeamId`, `draft_picks=[]`, `waiver_bid=bidAmount`, `week=scoringPeriodId`, `created=processDate or proposedDate`, unknown player → `player_name=None`); verify unit tests cover type mapping, add/drop attribution, created fallback, and unknown player.
- [x] 2.3 In `_register_espn_raw_data`, collect `transactions` records and return `compile_espn_transactions(...)` under the `"transactions"` grouped key (building `player_by_id` from the season's `player_scoring_totals`); verify a unit/component test shows the grouped dict includes `transactions`.
- [x] 2.4 Add an `"ESPN"` key to `QUERIES["TRANSACTIONS"]` in `src/processor/queries.py` (same passthrough SQL as `"SLEEPER"`); verify the ESPN transactions transform selects rows newest-first.
- [x] 2.5 Relax the transactions schema-build guard in `handler.py` from `platform == "SLEEPER" and grouped.get("transactions")` to `grouped.get("transactions")` (keep `chunked=True`); verify an ESPN league with transactions appends `TRANSACTIONS_SCHEMA`.

## 3. Backend — tests & docs

- [x] 3.1 Add a backend component scenario (`tests/component/`) driving the ESPN onboarder→processor chain with a mocked `mTransactions2` response, asserting `TRANSACTIONS#{season}` items are written and returned via the query path, and that an empty/absent transactions payload writes none; verify with `pipenv run behave tests/component`.
- [x] 3.2 Update `docs/db/dynamodb_spec.md` TRANSACTIONS section: ESPN now writes current-season `TRANSACTIONS#{season}` items (`draft_picks` always empty, only `waiver`/`free_agent` types); verify the "ESPN has no equivalent" wording is gone.
- [x] 3.3 Run `pipenv run ruff check --fix . && pipenv run ruff format .` and the affected `pytest tests/unit/...`; verify lint/format clean and coverage stays near 100% including error paths.

## 4. Frontend — nav & page

- [x] 4.1 In `frontend/src/features/sidebar/app-sidebar.tsx`, show the Transactions nav item for both ESPN and Sleeper (drop the `SLEEPER`-only condition, keep the after-Draft-Grades placement); update the comment. Verify via the updated nav-gating test.
- [x] 4.2 In `frontend/src/features/transactions/transactions.tsx`, make the type filter platform-aware (ESPN: Waivers + Free Agents, default Free Agents; Sleeper unchanged) and hide the summary-table Trades column for ESPN; verify via the updated transactions test.
- [x] 4.3 Drop "Sleeper-only" wording in `frontend/src/components/api/types.ts` and `frontend/src/features/transactions/api-calls.ts` doc comments (no logic change); verify the files build.

## 5. Frontend — tests

- [x] 5.1 Update `frontend/src/features/sidebar/__tests__/transactions-nav-gating.{feature,steps.test.tsx}` so the nav appears for ESPN too; verify with `npx vitest run src/features/sidebar`.
- [x] 5.2 Add ESPN scenarios to `frontend/src/features/transactions/__tests__/transactions.{feature,steps.test.tsx}` (default Free Agents, offers only Waivers/Free Agents, waiver/free-agent cards render adds/drops, summary omits Trades column, past-season empty state); verify with `npx vitest run src/features/transactions`.
- [x] 5.3 Run `npm run format:fix && npm run lint` from `frontend/`; verify clean.

## 6. Spec Purpose sync

- [x] 6.1 During apply, update the main-spec Purpose lines that call transactions "Sleeper-only" (`openspec/specs/backend/sleeper-transactions/spec.md` and `openspec/specs/frontend/transactions/spec.md`) so the specs don't drift; verify wording reflects ESPN + Sleeper.

## 7. End-to-end verification

- [ ] 7.1 Onboard/refresh a real ESPN league with current-season activity; confirm `TRANSACTIONS#{season}` items are written (query API returns rows) and the `/transactions` page shows the ESPN nav item plus waiver/free-agent cards.
