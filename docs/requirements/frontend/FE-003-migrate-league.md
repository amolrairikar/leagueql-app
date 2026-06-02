# FE-003: Migrate League

## Description
The `/migrate_league` multi-step flow migrates an onboarded league to a new platform while
preserving all-time history. Step 1 confirms the current (source) league. Step 2 collects
the destination platform + league ID (and ESPN cookies/season if destination is ESPN).
A further step maps each source-platform manager to a destination-platform member, then
submits to `POST /leagues/{leagueId}/migrate` and polls until the job completes.

## Scope
- Route: `/migrate_league` (protected) (`src/app/app.tsx`).
- Component: `src/features/migrate_league/migrate-league.tsx`; API in `api-calls.ts`.
- Uses [BE-009](../backend/BE-009-espn-members-proxy-api.md) to list ESPN members;
  triggers [BE-003](../backend/BE-003-league-migration.md); polls
  [BE-008](../backend/BE-008-job-status-tracking.md).

## Edge Cases
- **Manager left the league:** mapping must allow marking a manager as not returning
  (`__not_returning__`).
- **ESPN destination:** requires season + `s2`/`swid`; fetch destination members via the
  ESPN members proxy.
- **Destination already onboarded:** backend returns `409`; surface a clear message.
- **Operation already in progress:** backend returns `409`; surface and block re-submit.
- **Unmapped managers:** validation must require every source manager be mapped (or
  explicitly marked not returning) before submit.
- **Long-running job:** same ~120s pipeline; poll long enough to observe completion.
- **Cookies handling:** ESPN credentials transmitted once, cleared after use, never logged.

## Acceptance Criteria
- [ ] The flow confirms the source league, collects destination platform + league ID, and
      builds a manager mapping.
- [ ] ESPN destination members are fetched via the proxy and shown for mapping.
- [ ] Every source manager must be mapped or marked not returning before submission.
- [ ] Submitting calls migrate and polls job status to completion, surfacing `409`/failure
      messages.
- [ ] On success the user lands in the app with unified cross-platform history.

## Sources
`src/features/migrate_league/`, `src/app/app.tsx`.
