# Tasks

## 1. Implementation

- [x] 1.1 In `frontend/src/features/manager_comparison/manager-comparison.tsx`:
  - wrap the comparison grid in an `overflow-x-auto` container
  - size the grid `w-max min-w-full`
  - change the mobile page track to `minmax(0,1fr)` and give the left column `min-w-0`

## 2. Verification

- [x] 2.1 In a headless browser at a mobile width with one long username, check that:
  - both manager columns have equal width
  - the grid scrolls horizontally
  - the page itself doesn't overflow
- [x] 2.2 From `frontend/`, run:
  - `npm run format:fix`
  - `npm run lint`
  - `npm run build:ci`
  - `npx vitest run src/features/manager_comparison`
- [x] 2.3 Run `npx @fission-ai/openspec@latest validate --all`.
