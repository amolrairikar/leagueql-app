# FE-027: Transactions

## Description
The `/transactions` page lists a season's completed transactions — waivers, trades, and
free-agent moves — for the connected league, newest first. Each transaction shows its type,
week, date, and (for waivers) FAAB bid, with the players/picks each involved team added
(green) and dropped (red). A season selector switches between onboarded seasons and a type
filter narrows to All / Trades / Waivers / Free Agents.

This is a **Sleeper-only** feature ([BE-019](../backend/BE-019-sleeper-transactions.md)): the
nav entry is shown only when the connected league's platform is `SLEEPER`. ESPN exposes no
transaction data.

## Scope
- Route: `/transactions` (protected, app layout) — `src/app/app.tsx`.
- Component: `src/features/transactions/transactions.tsx`; API in `api-calls.ts`
  (`getTransactions` → `queryLeague` with `TRANSACTIONS#{season}`).
- Types: `TransactionItem` and friends in `src/components/api/types.ts`.
- Season selector: `src/features/season_select/season-select.tsx`.
- Sleeper-only nav gating: `src/features/sidebar/app-sidebar.tsx` (`sleeperOnlyNavItems`,
  appended only when `getLeagueCookies().platform === 'SLEEPER'`).
- Demo mode: `TRANSACTIONS` registered in `src/lib/demo-api.ts` (resolves to an empty set
  when the demo dataset has no transactions).

## Edge Cases
- **Sleeper-only nav:** the Transactions sidebar item is hidden for ESPN leagues.
- **Empty season:** a season with no completed transactions (the API 404s) renders an empty
  state, not an error — `getTransactions` maps a 404 to an empty list.
- **Load failure:** non-404 failures surface inline via the shared `Result`/`toResult`
  pattern (no global error banner).
- **Unknown player:** a player with no resolved name falls back to `Player {id}`; missing
  position is omitted.
- **Trades with picks:** draft picks acquired/sent render alongside player adds/drops.
- **Default season:** defaults to the most recent onboarded season.

## Acceptance Criteria
- [ ] `/transactions` lists the selected season's completed transactions newest-first, with
      type, week, and per-team adds (green) / drops (red).
- [ ] The Transactions nav item appears for Sleeper leagues and is hidden for ESPN leagues.
- [ ] The season selector lists all onboarded seasons and defaults to the latest; the type
      filter narrows by transaction type.
- [ ] A season with no transactions shows an empty state; a load error shows an inline error.
- [ ] Waiver FAAB bids and traded draft picks are displayed when present.

## Sources
`src/features/transactions/`, `src/features/sidebar/app-sidebar.tsx`, `src/app/app.tsx`,
`src/components/api/types.ts`, `src/lib/demo-api.ts`.
