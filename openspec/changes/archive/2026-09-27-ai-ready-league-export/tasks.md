# Tasks

## 1. Export guide builders

- [x] 1.1 Create `frontend/src/lib/export-guide.ts`:
  - `EXPORT_VIEW_DOCS` (summary, fields, notes, per-platform notes for the eight export views)
  - `ExportMeta` type
  - `buildExportManifest(bundle, meta)` and `buildExportReadme(bundle, meta)`, tailored to the
    views, seasons, and platform present, with an "undocumented view" fallback

  Verify with the unit tests in 3.1.

## 2. ZIP + dialog

- [x] 2.1 In `frontend/src/lib/download.ts`, extend `downloadLeagueZip(filename, bundle, meta)` to
  also write `README.md` and `manifest.json` at the ZIP root. Verify with 3.2.
- [x] 2.2 In `frontend/src/features/export_league/export-league-dialog.tsx`:
  - pass `{ leagueId, platform, exportedAt }` to `downloadLeagueZip`
  - add the AI-assistant hint with example prompts

  Verify with 3.3.

## 3. Tests

- [x] 3.1 Add `frontend/src/lib/__tests__/export-guide.test.ts`:
  - the README lists only included files and views
  - the ESPN caveat appears only for ESPN
  - an undocumented view is listed without throwing
  - manifest seasons, files, and row counts are correct
- [x] 3.2 Add `frontend/src/lib/__tests__/download.test.ts`: stub `URL.createObjectURL`, capture the
  blob, reload it with JSZip, and assert `README.md`, `manifest.json`, and `<season>_<view>.json`
  entries exist.
- [x] 3.3 Update `frontend/src/features/export_league/__tests__/export-league.feature` +
  `.steps.test.tsx`:
  - the ZIP assertion expects the `meta` argument
  - add an "AI hint shown" scenario

## 4. Quality gates

- [x] 4.1 From `frontend/`, run:
  - `npm run format:fix`
  - `npm run lint`
  - `npm run build:ci`
  - `npx vitest run src/lib src/features/export_league`
- [x] 4.2 Run `npx @fission-ai/openspec@latest validate --all`.
