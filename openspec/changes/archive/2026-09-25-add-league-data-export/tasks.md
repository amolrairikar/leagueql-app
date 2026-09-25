## 1. Backend — shared view-read helper

- [x] 1.1 Extract a `read_view(canonical_league_id, sk_base, suffix, *, use_prefix)` helper in
  `src/api/helpers.py` from the inline read in `query_league` (exact `get_item` vs. paginated
  `begins_with`-concat), returning the concatenated `data` list or `None`. Verify with new unit
  tests for the helper (single-item, prefix-concat, pagination, missing).
- [x] 1.2 Refactor `query_league` (`src/api/routes.py`) to call the new helper; verify the existing
  `TestQueryLeagueEndpoint`/`TestQueryLeagueMemberGate` suites still pass unchanged.

## 2. Backend — export endpoint

- [x] 2.1 Add `ExportResponse` model in `src/api/main.py` (`data: dict[str, dict[str, list]]`) and
  reuse `QUERY_TYPE_TO_SK_BASE` for the view→SK mapping; verify import/typing via `pytest` collection.
- [x] 2.2 Implement `GET /leagues/{leagueId}/export` handler `export_league` in `src/api/routes.py`:
  parse comma-separated `seasons` (400 if missing/empty), `lookup_league` → `get_league_metadata`
  → `require_league_member`, validate seasons against `get_league_seasons` (404 if none), then per
  season assemble every available view via `read_view` (single-item + prefix views), filter `TEAMS`
  to the season, omit empty views, `convert_decimals`, and set `Cache-Control: private, max-age=300`.
  Verify with the unit tests in task 5.1.
- [x] 2.3 Document `/leagues/{leagueId}/export` in `docs/api/openapi_spec.yaml` following the
  `queryLeague` entry (path/platform/`seasons` params, `ClerkJWT` security, aws_proxy integration,
  new `ExportResponse` schema); verify it parses (`openspec`/yaml lint or app boot).

## 3. Frontend — export feature

- [x] 3.1 Add **jszip** to `frontend/package.json` and install; verify `npm install` succeeds and it
  imports in a test.
- [x] 3.2 Add `downloadLeagueZip(filename, bundle)` in `frontend/src/lib/download.ts` that builds a
  ZIP (one `<season>_<view>.json` per view) and triggers a browser download (`Blob` →
  `createObjectURL` → anchor click → `revokeObjectURL`); verify via a unit/component test that spies
  on it.
- [x] 3.3 Add `ExportLeagueResponse` type in `frontend/src/components/api/types.ts` and
  `exportLeague(leagueId, platform, seasons)` in `frontend/src/components/api/leagues.ts` using
  `apiClient.get` with the `seasons` query param; verify with the frontend component test in 5.3.
- [x] 3.4 Create `frontend/src/features/export_league/export-league-dialog.tsx` (controlled
  `{ open, onOpenChange }`, seasons from `getLeagueCookies()`, per-season + "Select all" checkboxes,
  export disabled until ≥1 selected, `<Spinner>` while loading, `<ErrorAlert>` on failure, download
  on success); verify with the frontend component test in 5.3.

## 4. Frontend — sidebar, changelog

- [x] 4.1 Wire an "Export League Data" `SidebarMenuItem` into the non-demo, member-visible section of
  `frontend/src/features/sidebar/app-sidebar.tsx` (outside the `{isOwner && ...}` block) that opens
  the dialog via `useState`; render `<ExportLeagueDialog>` alongside the other controlled dialogs.
  Verify the button renders for a non-owner in the sidebar test.
- [x] 4.2 Prepend a `1.10.0` release to `CHANGELOG` in
  `frontend/src/features/changelog/constants.ts` with an "Added" bullet describing the export
  feature; verify the changelog page renders it (existing changelog tests / manual `/changelog`).

## 5. Tests

- [x] 5.1 Add `TestExportLeagueEndpoint` in `tests/unit/api/test_endpoints.py` (multi-season/multi-
  view bundle, transactions chunk concat, TEAMS season filter, empty views omitted, decimals,
  400/404/403, `Cache-Control`) + `TestReadView` in `test_utils.py`; verify `pipenv run pytest
  tests/unit` passes with ~100% coverage.
- [x] 5.2 Add `tests/component/features/api_export.feature` + steps (reuse the view-seeding step in
  `tests/component/steps/api_steps.py`); verify `pipenv run behave tests/component` passes.
- [x] 5.3 Add `frontend/src/features/export_league/__tests__/export-league.feature` +
  `export-league.steps.test.tsx` (seasons render, select-all, disabled with none, successful export
  calls endpoint + invokes download util, error shows `<ErrorAlert>`); add an MSW handler for
  `GET /leagues/:id/export` in `frontend/src/test/msw/server.ts`; verify
  `npx vitest run src/features/export_league` passes.

## 6. Verification

- [x] 6.1 `openspec validate --all` is green.
- [x] 6.2 Lint/format both stacks: `pipenv run ruff check --fix . && pipenv run ruff format .`;
  from `frontend/`: `npm run format:fix && npm run lint`.
- [x] 6.3 Full test suites pass: `pipenv run pytest tests/unit`, `pipenv run behave tests/component`,
  and from `frontend/` `npm run test`.
- [x] 6.4 Manual end-to-end: run the app, open a connected league, click "Export League Data", select
  seasons, and confirm a `.zip` downloads containing the expected per-view-per-season JSON.
