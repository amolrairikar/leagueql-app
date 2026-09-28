# Tasks

## 1. Ranking helpers

- [x] 1.1 Create `frontend/src/features/transactions/transaction-impact.ts` with `involvedRosterIds`, `teamLabel`, `sideTotal`, `netPickupValue`, `transactionImpact`, and `topTransactions`, built on `rosPointsFor` / `WeeklyPlayerPoints`. Verify with `npm run build:ci`.
- [x] 1.2 Move `TYPE_META` / `typeMeta` into `frontend/src/features/transactions/type-meta.ts` and refactor `transactions.tsx` (`TeamPanel`, `TransactionCard`) to use the shared helpers so cards and tiles share one implementation. Verify existing transactions tests still pass.

## 2. UI

- [x] 2.1 Create `frontend/src/features/transactions/top-transactions.tsx` rendering the stat-tile row (rank, type chip, impact value + label, team avatar/name, adds/drops, meta line; #1 tinted; `grid-cols-2 sm:grid-cols-3 lg:grid-cols-5`). Verify visually with `npm run dev`.
- [x] 2.2 Render it in `transactions.tsx` below the ESPN disclaimer and above the Summary label, hidden when matchups failed or nothing is eligible, independent of the type filter.

## 3. Tests & quality

- [x] 3.1 Add scenarios to `__tests__/transactions.feature` + steps: ranked mixed top list, trade tile credits the winner, fewer than five / non-positive excluded, nothing eligible hides the section, box scores unavailable hides the section, type filter doesn't change it. Verify with `npx vitest run src/features/transactions`.
- [x] 3.2 Run `npm run format:fix`, `npm run lint`, `npm run build:ci` from `frontend/` and `npx @fission-ai/openspec@latest validate --all`; verify all are clean.
