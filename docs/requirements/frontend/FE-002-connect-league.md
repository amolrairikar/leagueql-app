# FE-002: Connect League (Onboarding Flow)

## Description
The `/connect_league` flow lets a signed-in user onboard a new league or refresh an existing
one. The user selects a platform (ESPN/Sleeper), enters a league ID (and latest season +
ESPN cookies for private ESPN leagues), submits to `POST /leagues`, then polls
`GET /jobs/{jobId}` until the job completes or fails. On success the user is routed into the
app.

## Scope
- Route: `/connect_league` (protected) (`src/app/app.tsx`).
- Component: `src/features/connect_league/league-connect.tsx`; schema
  `league-connect-schema.ts`; API in `api-calls.ts`.
- Triggers [BE-001](../backend/BE-001-league-onboarding.md) /
  [BE-002](../backend/BE-002-league-refresh.md); polls
  [BE-008](../backend/BE-008-job-status-tracking.md).

## Edge Cases
- **Private ESPN league:** requires `espn_s2` + `SWID`; cookies are transmitted once over
  HTTPS and cleared (`clearEspnCookies`) on success — never persisted or logged.
- **Chrome extension auto-fill:** ESPN cookies may be auto-filled by the extension
  ([EXT-001](../extension/EXT-001-espn-cookie-autofill.md)); the form must also accept
  manual entry.
- **Pre-filled league:** when arriving with a known platform + league ID, those fields are
  locked against edits.
- **Long-running job:** the processor can take up to ~120s; polling must run long enough to
  observe `COMPLETED` rather than falsely timing out.
- **Job failure:** display the backend `failure_reason` (e.g. expired ESPN cookies) and
  allow retry.
- **Lookup / submit failure:** a non-404 failure of the initial `getLeague` lookup, or an
  exhausted-retry failure of the `POST /leagues` submit (network / 5xx), is surfaced inline in
  the form's failed-state alert rather than silently aborting. (A 404 from the lookup is the
  normal "not onboarded yet" signal and routes to onboarding, not an error.) There is no global
  error banner.
- **Already onboarded:** backend may return "already onboarded"; route the user in rather
  than erroring.
- **Validation:** league ID must be numeric; ESPN requires a season.
- **Demo mode:** connecting is disabled/redirected in demo mode.

## Acceptance Criteria
- [ ] A user can onboard a public Sleeper or ESPN league with platform + league ID
      (+ season for ESPN).
- [ ] Private ESPN onboarding accepts `s2`/`swid` via extension auto-fill or manual entry,
      and clears them on success.
- [ ] The UI polls job status and shows in-progress, success, and failure states with the
      backend-provided failure message.
- [ ] Polling persists long enough to capture completion of slow (~120s) jobs.
- [ ] Pre-filled platform/league ID fields are locked.
- [ ] On success the user is routed into the app (home).
- [ ] ESPN credentials never appear in logs or persistent storage.

## Sources
`src/features/connect_league/`, `src/app/app.tsx`.
