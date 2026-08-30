# Tasks

## 1. Extract shared logic (no behavior change)
- [x] 1.1 Create `frontend/src/features/draft_grades/compute-draft-grades.ts`: move the grading
      constants (`STEAL_DELTA_MIN`, `BUST_*`) and best/worst-pick + steal/bust selection out of
      `draft-grades.tsx`; export pure functions (`gradeDraftForTeam(picks, teamId)` →
      `{ bestPick, worstPick, steals, busts, scorablePicks }`). Refactor `draft-grades.tsx` to
      import them; keep behavior identical.
- [x] 1.2 Create `frontend/src/features/transactions/compute-trade-value.ts`: move `sideTotal` and
      the per-trade winner/margin logic out of `transactions.tsx`; export
      `tradeValueForRoster(txn, rosterId, weekly)` and `evaluateTrade(txn, weekly)`. Refactor
      `transactions.tsx` to import them; keep behavior identical.
- [x] 1.3 Update `draft_grades` and `transactions` unit/component tests to cover the extracted
      modules directly.

## 2. New feature scaffolding & data
- [x] 2.1 Add persisted team selection to `frontend/src/lib/cookie-handler.ts`:
      `getMyTeamOwnerId(leagueId)` / `setMyTeamOwnerId(leagueId, ownerId)` backed by
      `localStorage` key `myTeamOwnerId:{leagueId}`.
- [x] 2.2 Create `frontend/src/features/my_team/api-calls.ts`: fetch, for a season,
      `SEASON_STANDINGS#`, `MATCHUPS#`, `DRAFT#`, and (Sleeper) `TRANSACTIONS#` via `queryLeague`;
      expose a single `getMyTeamData(leagueId, platform, season)` returning a `Result`-friendly
      bundle, reusing existing fetchers. (Power-ranking movement is derived from `MATCHUPS`
      through-prior-week, so no separate `WEEKLY_STANDINGS` fetch is needed.)
- [x] 2.3 Build the manager/team roster + selector data (reuse the derivation from
      `manager-comparison.tsx`), keyed by `owner_id`, resolving to the season's `team_id`.

## 3. New compute modules (pure, unit-tested)
- [x] 3.1 `my_team/compute-power-rankings.ts` — score = blend of `avg_pf` (0.5), all-play win %
      (0.3), last-3-week form (0.2) from `MATCHUPS`; rank + movement vs the ranking recomputed
      through the previous week.
- [x] 3.2 `my_team/compute-grade.ts` — composite (all-play 0.40, PF percentile 0.30, win % 0.20,
      lineup-efficiency percentile 0.10) → league percentile → letter bands (per `design.md`).
- [x] 3.3 `my_team/compute-team-metrics.ts` — assemble per-team metrics: record/standing, PF rank,
      all-play, luck (`computeExpectedWins`), SoS (`computeStrengthOfSchedule`), season lineup
      efficiency + points-left (aggregate `computeStartSitReport` over the team's weeks), recent
      form, best/worst pick (`compute-draft-grades`), best/worst trade (`compute-trade-value`).
- [x] 3.4 `my_team/compute-insights.ts` — rule catalog `{ id, sentiment, applies, score, render }`;
      engine fires applicable rules, ranks by `score`, returns top N + the hero verdict from the top
      theme; trade rules guarded on Sleeper + trades present.

## 4. Page UI — `my_team/my-team.tsx`
- [x] 4.1 Page shell following `home-page.tsx`: `getLeagueCookies()`, `useMemo` promises via
      `toResult`, `<Suspense>` + `<Skeleton>` per section, inline `<ErrorAlert>` on failure.
- [x] 4.2 Header: team `<select>` (persisted) + `SeasonSelect`.
- [x] 4.3 Sections: hero (grade + verdict), KPI row, recent form + stack-up meters, Draft Report +
      Trade Report, Insights list — using `bg-card border border-border/50 rounded-lg` panels,
      `text-[11px] uppercase tracking-[0.08em]` labels, `TeamAvatar`, and `lib/color-constants`.
- [x] 4.4 ESPN: Trade Report renders a graceful "available on Sleeper" state; trade insights absent.

## 5. Navigation & route
- [x] 5.1 Add `{ title: 'My Team', url: '/my_team', icon: … }` near the top of `navItems` in
      `frontend/src/features/sidebar/app-sidebar.tsx`.
- [x] 5.2 Register `/my_team` in `frontend/src/app/app.tsx` `APP_LAYOUT_ROUTES`.

## 6. Tests
- [x] 6.1 Component tests (`my_team/__tests__/`, jest-cucumber + MSW): team selection re-filters all
      sections; persisted default; Sleeper vs ESPN (trade report gated); loading / empty / error;
      insight firing + ordering; grade reflects strength over record.
- [x] 6.2 Unit tests for each `compute-*` module (power rankings, grade bands, insights rules +
      ranking + guards, team metrics incl. efficiency aggregation).
- [x] 6.3 Run `npx vitest run src/features/my_team src/features/draft_grades src/features/transactions`.

## 7. Lint & validate
- [x] 7.1 `npm run format:fix` and `npm run lint` from `frontend/`.
- [x] 7.2 `npm run build:ci` (tsc) clean.
- [x] 7.3 `openspec validate add-my-team-page --strict`.
