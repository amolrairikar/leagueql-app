## 1. Scenario engine

- [x] 1.1 In `frontend/src/features/playoff_race_predictor/compute-projection.ts`, export types `ClinchCategory` (`'win-and-in' | 'must-win' | 'controls-destiny'`), `TieMargin` (`{ rival: PredictorTeam; gap: number }`), `ClinchScenario`, and `ClinchScenarios`.
- [x] 1.2 Derive clinched/eliminated directly from the enumeration (a team `in` in every combo is clinched; `out` in every combo is eliminated) rather than a separate bound — exact and self-consistent, so no `computeEliminated` helper is needed.
- [x] 1.3 Add exported `computeClinchScenarios(model, picks): ClinchScenarios | null`, mirroring the `computePlayoffOdds` setup (baseWins with picks folded in, fixed points-for, `freeA`/`freeB` for un-picked matchups, plus each team's earliest un-picked game + opponent). Return `null` when `numFree > MAX_EXACT_MATCHUPS`. Exclude teams that are clinched or eliminated (per the enumeration). Enumerate all `2^numFree` combos; per live team classify each combo `in`/`out`/`tie`, and by the team's next-game bit derive `win-and-in` / `must-win` / `controls-destiny`, collecting tie rivals + `gap = pf[T] − pf[rival]`. Return `null` if the emitted list is empty.
- [x] 1.4 Unit tests in `__tests__/compute-projection.test.ts`: the verified final-week cluster (four win-and-in teams with correct tie-margin gaps), a controls-destiny case, a must-win case, clinched-by-record and eliminated teams omitted, `numFree > MAX_EXACT_MATCHUPS` → `null`, no live clean line → `null`, and a pick that moves a team between categories.

## 2. Clinching-scenarios UI

- [x] 2.1 In `playoff-race-predictor.tsx`, add a `ClinchScenarios` component (its own `useMemo(() => computeClinchScenarios(model, picks), [model, picks])`) rendered as a sibling after `<StandingsTable />` in `PredictorTool`; render nothing when `null`.
- [x] 2.2 Card + rows: `bg-card border border-border/50 rounded-lg` with the shared eyebrow label; reuse `TeamAvatar`, `avatarColor`, `cn`. Win-and-in / controls-destiny use `text-primary` + `bg-primary/10`; must-win uses amber. Copy has no week number and formats each `TieMargin` by sign ("leads {rival} by {gap}" / "trails {rival} by {-gap}"). Footer notes ties are decided by points-for including points still to be scored, with the assumed-count caveat when `numPlayoffTeamsAssumed`.
- [x] 2.3 Add the one-line explainer near the section: "Odds show how likely; scenarios show what's locked."
- [x] 2.4 Add jest-cucumber scenarios in `__tests__/playoff-race-predictor.feature` + `.steps.test.tsx`: section appears when a game is decisive, updates when a winner is picked, and is hidden when nothing is decided.

## 3. Demo (replay) mode

- [x] 3.1 Confirmed the section renders in demo replay over `src/lib/demo-data.json` (2025 season yields must-win scenarios) and extended `src/features/demo/__tests__/demo-mode.*` to assert it.

## 4. Validate

- [x] 4.1 From `frontend/`: `npm run format:fix` and `npm run lint` (clean).
- [x] 4.2 From `frontend/`: `npx vitest run` — full suite green (331 tests).
- [x] 4.3 From repo root: `openspec validate --all`.
