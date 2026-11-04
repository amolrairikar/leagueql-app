# Tasks

## 1. Frontend export fan-out

- [x] 1.1 In `frontend/src/features/export_league/export-league-dialog.tsx`, request each selected season separately via `exportLeague(leagueId, platform, [season])` with concurrency 3, merge the `data` into one bundle, and call `downloadLeagueZip` once; verify with the updated component test asserting one request per season and a single download call.
- [x] 1.2 Treat a per-season 404 as "no data" (omit it), abort on any other error without starting remaining seasons, and show an inline error when all seasons are omitted; verify with component tests for the failure and all-empty scenarios.
- [x] 1.3 Compute `exportedAt` once before the requests and keep loading/disabled state for the whole run; verify the existing loading scenario still passes.

## 2. Tests

- [x] 2.1 Update `features/export_league/__tests__/export-league.feature` and `.steps.test.tsx`: replace the single `seasons "2023,2024"` request assertion with a per-season request assertion and merged-bundle download; run `npx vitest run src/features/export_league` from `frontend/`.
- [x] 2.2 Add scenarios for one season returning 500 (inline error, no download) and one season returning 404 (omitted, download proceeds); run the same vitest command.

## 3. Quality and specs

- [x] 3.1 Run `npm run format:fix`, `npm run lint`, and `npm run build:ci` from `frontend/`; all pass.
- [x] 3.2 Run `npx @fission-ai/openspec@latest validate --all`; passes with the delta spec.
