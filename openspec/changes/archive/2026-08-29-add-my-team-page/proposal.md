# My Team report card page

## Why
Every analytics page in LeagueQL is league-wide (standings, matchups, draft grades, transactions).
There is no single view that answers the most personal question a manager has — **"how is *my*
team doing?"**. Today they must visit five pages and stitch the story together themselves.

This adds a new **`/my_team`** page: a personal report card that filters every relevant insight to
one team and surfaces the takeaways — record & luck, power-ranking spot, recent form, best/worst
draft picks, best/worst trades, bench efficiency, strength of schedule — on one scannable screen,
topped by an overall letter grade and a short written verdict.

Everything is **computed entirely client-side** from precomputed views that are already fetchable
(`SEASON_STANDINGS`, `WEEKLY_STANDINGS`, `MATCHUPS`, `DRAFT`, `TRANSACTIONS`). The written verdict
and insight sentences are assembled **deterministically from those computed facts via string
templates** — no LLM, no new backend endpoint, no data-model change.

## What Changes
- **New `/my_team` page** with a team picker in its header. The app has no viewer→team mapping
  (only a league-level `is_owner` flag), so the user selects which team is "theirs"; the choice is
  persisted per league in `localStorage` and defaults to the first team. Season is chosen with the
  existing season selector.
- **Sections:** hero (identity + overall grade + templated verdict); a KPI row (record, standing,
  power rank + movement, points-for + league rank, all-play record, luck); recent form + "how you
  stack up" meters; a Draft Report (best/worst pick) and Trade Report (best/worst trade) side by
  side; and an Insights list.
- **Overall grade** — a deterministic, league-relative letter grade from a weighted blend of
  all-play win %, points-for percentile, actual win %, and lineup efficiency (see `design.md`).
- **Insights** — a rule catalog: each insight type is a predicate + a severity score + one
  parameterized sentence template, filled from computed metrics; the engine fires the applicable
  rules, ranks them, and renders the top handful (see `design.md`).
- **Power rankings** — a new client-side computation (blend of avg PF, all-play, recent form) with
  week-over-week movement, used by this page (the one net-new metric).
- **Reuse & extraction:** reuse `compute-sos`, `computeExpectedWins`, `computeStartSitReport`,
  `buildWeeklyPlayerPoints`/`rosPointsFor`. The best/worst-pick grading (in `draft-grades.tsx`) and
  the per-trade value logic (`sideTotal` in `transactions.tsx`) are extracted into shared, exported,
  unit-tested modules so the new page and the existing pages share one implementation.
- **Navigation:** add a "My Team" entry to the sidebar and register the route.
- **ESPN gating:** transactions are Sleeper-only, so the Trade Report and trade-based insights show
  a graceful "available on Sleeper" state on ESPN; every other section works on both platforms.

## Impact
- Affected specs: **new** `frontend/my-team`; **modified** `frontend/navigation-sidebar` (adds the
  My Team link).
- Affected code: **new** `frontend/src/features/my_team/`; **refactor** (extract logic, no behavior
  change) `frontend/src/features/draft_grades/` and `frontend/src/features/transactions/`;
  **edit** `frontend/src/features/sidebar/app-sidebar.tsx`, `frontend/src/app/app.tsx`,
  `frontend/src/lib/cookie-handler.ts`.
- Tests: new component + unit tests under `my_team/`; updated tests for the refactored draft-grades
  and transactions modules.
- No backend, DynamoDB, OpenAPI, or architecture-diagram changes.
