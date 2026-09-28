# Proposal

## Why

Handing a league export to a general-purpose AI assistant (Claude, ChatGPT, a local model) gives it
the same processed views a hosted MCP server would expose. Those views sit behind `/query`, and
`/export` bundles the same data, so the export can deliver conversational analysis (cross-view
synthesis, long-tail questions, recaps/roasts) at close to zero infrastructure cost. Today, though,
the ZIP is a bare set of `<season>_<view>.json` files with no explanation. An assistant has to guess
what fields mean, how files join, and platform quirks: ESPN transactions cover only the current
season, views with no data are omitted, and playoff-team counts may be assumed. Adding that context
to the export (the job MCP tool descriptions would otherwise do) lets us see whether users want
AI analysis before building an MCP server.

## What Changes

- The export ZIP gains a root `README.md` data guide. It covers what the export is (league id,
  platform, seasons, export time), the files it contains, a per-view data dictionary with join keys,
  platform caveats relevant to this export, and example questions to ask an AI assistant.
- The export ZIP gains a root `manifest.json` describing the export in machine-readable form (league
  id, platform, export time, seasons, and each file's season/view/row count).
- The export dialog shows a short hint that the ZIP can be uploaded to an AI assistant, with a few
  example prompts.
- The existing `<season>_<view>.json` files and their naming are unchanged.

## Capabilities

### New Capabilities

_None._

### Modified Capabilities

- `frontend/export-league-data`: the ZIP gains a `README.md` data guide and a `manifest.json`, and
  the dialog suggests AI-assistant usage.

## Impact

- **Frontend:**
  - new `frontend/src/lib/export-guide.ts` (view docs, README and manifest builders)
  - `frontend/src/lib/download.ts` (`downloadLeagueZip` takes export metadata and writes the two
    new files)
  - `frontend/src/features/export_league/export-league-dialog.tsx` (passes metadata; AI hint)
  - tests: new `frontend/src/lib/__tests__/export-guide.test.ts` and `download.test.ts`; updated
    `export_league/__tests__/export-league.*`
- **Backend / API / data model:** none. The ZIP is assembled client-side from the unchanged
  `GET /leagues/{leagueId}/export` response.
