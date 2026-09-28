# Tasks

## 1. Implementation

- [x] 1.1 In `frontend/src/features/manager_history/api-calls.ts`, have `withInProgressRanks` set
  `in_progress: true` on every row of an unfinalized season, reusing the existing
  `isFinalized` test, and add the optional `in_progress` field to `ManagerStandingsItem`.
- [x] 1.2 In `frontend/src/features/manager_history/manager-history.tsx`, make
  `SeasonEntry.result` `null` for in-progress seasons and skip rendering the badge when it is
  `null`.

## 2. Tests

- [x] 2.1 In `manager_history/__tests__/manager-history.feature` + `.steps.test.tsx`:
  - assert the in-progress season shows no result pill
  - assert a finalized champion season shows "Champion"

## 3. Quality gates

- [x] 3.1 From `frontend/`, run:
  - `npm run format:fix`
  - `npm run lint`
  - `npm run build:ci`
  - `npx vitest run src/features/manager_history`
- [x] 3.2 Run `npx @fission-ai/openspec@latest validate --all`.
