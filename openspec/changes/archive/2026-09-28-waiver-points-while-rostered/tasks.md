# Tasks

## 1. Helpers

- [x] 1.1 Add an exclusive `untilWeek = Infinity` bound to `rosPointsFor` in `frontend/src/features/transactions/api-calls.ts`. Verify existing tests pass.
- [x] 1.2 In `transaction-impact.ts`, add `RosterExits`, `buildRosterExits`, `exitWeek`; bound added players in `netPickupValue` by their exit week; thread `exits` through `transactionImpact` / `topTransactions`. Verify with `npm run build:ci`.

## 2. UI

- [x] 2.1 In `transactions.tsx`, build exits from the full season list, pass them to `TeamPanel`, show stint-bounded points on waiver/FA add rows, and rename the header to "Points while rostered".
- [x] 2.2 Have `topTransactions` bound pickups by their roster exits (built from the full season list it receives), and remove the Top transactions "Ranked by …" caption.

- [x] 2.3 Bound trade acquisitions the same way: `sideTotal` takes `exits`, trade add rows show points while rostered, and the side-total footer reads "Points while rostered".

## 3. Tests & quality

- [x] 3.1 Add scenarios (later dropped, later traded away, same-week drop, dropped player keeps full ROS, trade acquisition later dropped) and update the header assertion in `__tests__/transactions.feature` + steps. Verify with `npx vitest run src/features/transactions`.
- [x] 3.2 Run `npm run format:fix`, `npm run lint`, `npm run build:ci`, `npm run test` from `frontend/` and `openspec validate --all`; verify all are clean.
