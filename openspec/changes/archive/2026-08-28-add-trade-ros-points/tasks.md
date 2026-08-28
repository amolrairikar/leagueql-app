# Tasks

## 1. Data fetch & compute helpers
- [x] 1.1 Re-export `getSeasonMatchups` and `MatchupItem` from
      `frontend/src/features/transactions/api-calls.ts` (reuse the matchups feature's fetcher).
- [x] 1.2 Add `buildWeeklyPlayerPoints(matchups: MatchupItem[])` → `Map<string, Map<number, number>>`
      (player_id → week → points), iterating each row's four `PlayerStat[]` arrays; key by
      `String(player_id)` (PlayerStat ids are numbers, TransactionPlayer ids are strings) and
      week by `Number(row.week)`.
- [x] 1.3 Add `rosPointsFor(playerId, tradeWeek, weekly)` summing points for weeks `>= tradeWeek`,
      rounded to 2 dp; missing player → 0.

## 2. Fetch matchups on the page
- [x] 2.1 In `transactions.tsx`, add a `matchupsPromise` alongside the transactions/standings
      promises (same `toResult` pattern), fetching `getSeasonMatchups` for the selected season;
      tolerate failure (degrade silently).
- [x] 2.2 Thread the matchups result into `TransactionsBody` → `TransactionCard`; build the
      weekly-points map once per render from the result when `ok`.

## 3. Render (trade path only)
- [x] 3.1 `MoveRow`: accept an optional right-aligned points node
      (`ml-auto text-[12px] font-medium tabular-nums`); draft-pick rows pass `—` in muted text.
- [x] 3.2 `TeamPanel`: for trades with weekly points, compute each add's ROS points and the side
      total; render a footer ("Rest-of-season pts" + total) and mark the winning side (emerald
      tint + "Won" tag).
- [x] 3.3 `TransactionCard`: for a 2-roster trade, compare side totals and render the result pill
      ("<team> won by +N.NN pts", or "Even") plus the scope caption ("Week {week} → end of
      playoffs"). Gate all additions on `isTrade` and matchup data being present.

## 4. Tests
- [x] 4.1 Extend `transactions.feature` + `transactions.steps.test.tsx` (MSW mocks both
      `TRANSACTIONS` and `MATCHUPS`): per-player points + side totals + winner; window excludes
      pre-trade weeks; draft pick shows "—"; tie shows "Even"; graceful degradation when
      `MATCHUPS` 404s.
- [x] 4.2 Run `npx vitest run src/features/transactions`.

## 5. Lint & validate
- [x] 5.1 `npm run format:fix` and `npm run lint` from `frontend/`.
- [x] 5.2 `openspec validate add-trade-ros-points --strict`.
