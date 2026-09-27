## 1. Implementation

- [x] 1.1 In `frontend/src/features/matchups/matchup-preview.tsx`, make `Card` an `overflow-x-auto` scroll container with a `min-w-fit` inner wrapper, keeping the close button on the outer `relative` wrapper outside every card.
- [x] 1.2 Let the Recent Form header username wrap (`overflow-wrap: anywhere`) so that card fits the mobile viewport.

## 2. Tests

- [x] 2.1 Extend `frontend/src/features/matchups/__tests__/matchups.{feature,steps.test.tsx}` with a scenario asserting each preview card is its own horizontal scroll container, Recent Form usernames can wrap, and the close button sits outside every card.

## 3. Lint and verification

- [x] 3.1 From `frontend/`, run `npm run format:fix`, `npm run lint`, and the matchups tests; confirm all pass.
- [x] 3.2 Run `openspec validate --all` and confirm it passes.
