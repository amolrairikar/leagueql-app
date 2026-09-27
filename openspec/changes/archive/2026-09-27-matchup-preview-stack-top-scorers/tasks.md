## 1. Implementation

- [x] 1.1 In `frontend/src/features/matchups/matchup-preview.tsx`, make the Top Scorers grid `grid-cols-1 sm:grid-cols-2`, and give the right team's column a top divider on mobile that is removed from `sm` up.

## 2. Tests

- [x] 2.1 Extend `frontend/src/features/matchups/__tests__/matchups.{feature,steps.test.tsx}` with a scenario asserting the Top Scorers grid stacks on mobile (single column, `sm:grid-cols-2`) with the left team's list first.

## 3. Lint and verification

- [x] 3.1 From `frontend/`, run `npm run format:fix`, `npm run lint`, and the matchups tests; confirm all pass.
- [x] 3.2 Run `openspec validate --all` and confirm it passes.
