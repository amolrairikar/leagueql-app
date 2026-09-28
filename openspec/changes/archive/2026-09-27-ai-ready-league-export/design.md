# Design

## Context

See proposal.md, "Why". The export ZIP is built entirely in the browser. `ExportLeagueDialog` calls
`exportLeague` (`GET /leagues/{id}/export`), then `downloadLeagueZip(filename, bundle)` in
`frontend/src/lib/download.ts` writes one `<season>_<view>.json` per view per season with JSZip and
triggers the download. The bundle's view keys are fixed by the backend's `EXPORT_SEASON_VIEWS` plus
`teams` (`src/api/main.py`): `standings`, `weekly_standings`, `matchups`, `draft`, `transactions`,
`playoff_bracket`, `league_settings`, `teams`.

## Goals / Non-Goals

**Goals:**
- An AI assistant given only the ZIP can interpret every file correctly: field meanings, join keys,
  platform caveats.
- The guide describes only what is actually in this export, so it never documents views or
  platforms the user didn't get.
- A light, non-intrusive nudge in the dialog that the export can be used with an AI assistant.

**Non-Goals:**
- Any backend, API, or data-model change.
- Including frontend-computed derived metrics (schedule swap, draft grades, lineup efficiency, …)
  in the export. That is a possible follow-up.
- An MCP server or in-app chat.

## Decisions

- **Generate the guide client-side from a static docs map.** `EXPORT_VIEW_DOCS` in a new pure module
  `frontend/src/lib/export-guide.ts` maps each view name to a summary, per-field descriptions, and
  optional general and per-platform notes. `buildExportReadme` and `buildExportManifest` are pure
  functions of `(bundle, meta)`, so they are unit-testable without the DOM or JSZip. Alternative
  considered: a static README shipped from the backend. Rejected because the frontend already builds
  the ZIP, and a static file can't tailor itself to the included views and platform.
- **Tailor to the bundle.** The README lists only files present in the bundle, documents only views
  present, and includes platform notes only for the export's platform. A view key with no docs entry
  (e.g. a future backend view) gets a generic "undocumented view" line instead of throwing, so a
  backend addition never breaks exports.
- **Field docs sourced from the processed schema.** Descriptions come from `frontend/src/components/api/types.ts`
  and the processor output columns in `src/processor/queries.py` / `src/processor/handler.py`. Where
  a value's meaning isn't obvious, the docs say so explicitly:
  - `matchups.winner` is a team id or `"TIE"`
  - `draft.draft_rank_delta` = drafted position rank − actual position rank (negative = the player
    finished better than where they were drafted)
  - `vorp` is null for K and D/ST
- **`manifest.json` alongside the README.** It lets tools or agents enumerate files without parsing
  prose. Shape: `{ league_id, platform, exported_at, seasons, files: [{ path, season, view, row_count }] }`.
- **`downloadLeagueZip` takes a third `meta` argument** (`{ leagueId, platform, exportedAt }`). The
  dialog supplies `exportedAt` (`new Date().toISOString()`) so the builders stay deterministic in
  tests.

## Risks / Trade-offs

- **Docs drift from the processor schema.** Mitigation: the fallback for unknown views, plus the
  field docs are descriptive (unknown extra fields in rows don't break anything). A schema change
  to a view should update `EXPORT_VIEW_DOCS` in the same change.
- **README size.** It is a few KB of Markdown, negligible next to the matchup JSON.
