# Tasks

## 1. Frontend

- [x] 1.1 In `getAlts` (`frontend/src/features/draft_grades/draft-grades.tsx`):
  - return `[]` when the bust pick is a keeper
  - exclude candidates where `keeper` is true
- [x] 1.2 Add jest-cucumber scenarios to `draft-grades.feature` and `draft-grades.steps.test.tsx`:
  - keepers are not suggested as alternatives
  - a keeper bust shows no alternatives but still counts as a bust

## 2. Verify

- [x] 2.1 `npx vitest run src/features/draft_grades`, `npm run format:fix`, `npm run lint`,
  `npm run build:ci`
- [x] 2.2 `openspec validate --all`
