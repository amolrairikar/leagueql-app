## Why

Members can view a league's processed data (standings, matchups, drafts, transactions, …) one
page at a time in the app, but there is no way to pull that data **out** of LeagueQL for their own
analysis, archiving, or sharing. An export lets a member download the processed data for the
seasons they choose.

## What Changes

- Add a new backend endpoint `GET /leagues/{leagueId}/export?platform={P}&seasons=2023,2024` that
  returns the processed views for the selected seasons as one bundle, gated by the same league
  membership rule as `GET /leagues/{leagueId}/query`.
- Add an "Export League Data" action to the app sidebar, visible to **any league member** (not
  owner-only). It opens a dialog with a checkbox per onboarded season plus a "Select all" option.
- On confirm, the frontend downloads the selected seasons' processed data to the browser as a
  **ZIP of JSON files** — one `.json` per view per season (e.g. `2024_standings.json`).
- Add an entry to the in-app changelog describing the feature.
- Non-behavioral refactor: extract the single-view DynamoDB read (exact `get_item` vs. paginated
  `begins_with`-concat) from `query_league` into a shared helper reused by both endpoints.

No new deployed infrastructure — the endpoint only reads existing precomputed views from DynamoDB,
so the architecture diagram and DynamoDB schema are unchanged.

## Capabilities

### New Capabilities
- `backend/league-export`: Serve a member-gated bundle of processed league views for a caller-
  selected set of seasons via `GET /leagues/{leagueId}/export`.
- `frontend/export-league-data`: A sidebar dialog that lets a member pick seasons and download the
  league's processed data as a ZIP of per-view-per-season JSON files.

### Modified Capabilities
- `frontend/navigation-sidebar`: Add the member-visible "Export League Data" action to the sidebar.

## Impact

- **Backend:** new route `export_league` in `src/api/routes.py`; new `ExportResponse` model in
  `src/api/main.py`; extracted view-read helper in `src/api/helpers.py` (also refactors
  `query_league`). API contract updated in `docs/api/openapi_spec.yaml`.
- **Frontend:** new feature dir `frontend/src/features/export_league/` (dialog + API call); new
  reusable ZIP-download util in `frontend/src/lib/download.ts`; new **jszip** dependency in
  `frontend/package.json`; sidebar wiring in `frontend/src/features/sidebar/app-sidebar.tsx`; new
  changelog entry in `frontend/src/features/changelog/constants.ts`; new response type in
  `frontend/src/components/api/types.ts` and fetch fn in `frontend/src/components/api/leagues.ts`.
- **Tests:** backend unit (`tests/unit/api/test_endpoints.py`), backend component
  (`tests/component/features/api_export.feature` + steps), frontend component
  (`frontend/src/features/export_league/__tests__/`).
- **No infra/DynamoDB schema changes.**
