# Tasks

## 1. Frontend

- [x] 1.1 Replace `SeasonScheduleDialog` with an inline `SeasonSchedulePanel` (schedule + side-panel box score).
- [x] 1.2 Add an expandable `SeasonCard` (button header with `aria-expanded`, chevron, region body) and use it in
      `ManagerHistoryContent`, keyed by manager + season.

## 2. Tests

- [x] 2.1 Update the manager-history component tests to assert on the inline region instead of a dialog, and add
      scenarios for expand, collapse, multiple open seasons, and the in-card box score.

## 3. Quality

- [x] 3.1 Run `npm run format:fix`, `npm run lint`, `npm run build:ci`, vitest, and `openspec validate --all`.
