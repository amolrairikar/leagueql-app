# Tasks

## 1. Helpers

- [x] 1.1 Add `SeasonPhase` and `isRegularSeasonMatchup` to `frontend/src/lib/matchups.ts`, with unit tests in `lib/__tests__/matchups.test.ts`.
- [x] 1.2 Add `frontend/src/components/season-phase-toggle.tsx` (label/Switch/label, like the home page standings toggle).

## 2. UI

- [x] 2.1 In `matchup-records.tsx`, add phase state (default regular), extract records only from matchups in that phase, and render the toggle (clearing the selected row).
- [x] 2.2 Do the same in `player-records.tsx`, composing with the Season and Manager filters.

## 3. Tests & quality

- [x] 3.1 Add "excluded by default" and "toggle to Postseason" scenarios to both records `.feature` files + steps. Verify with `npx vitest run src/features/matchup_records src/features/player_records`.
- [x] 3.2 Run `npm run format:fix`, `npm run lint`, `npm run build:ci`, `npm run test` from `frontend/` and `openspec validate --all`; verify all are clean.
