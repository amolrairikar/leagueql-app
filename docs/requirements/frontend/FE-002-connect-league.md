# FE-002: Connect League (Onboarding Flow)

## Description
The `/connect_league` flow lets a signed-in user onboard a new league or refresh an existing
one. The user selects a platform (ESPN/Sleeper), enters a league ID (and latest season +
ESPN cookies for private ESPN leagues), submits to `POST /leagues`, then polls
`GET /jobs/{jobId}` until the job completes or fails. On success the user is routed into the
app.

The flow is ownership/membership aware (LQL-01 / BE-016). The initial `getLeague` existence
check distinguishes three outcomes — `404` (not onboarded → ONBOARD; the caller becomes
owner), `200` (already onboarded and readable), and `403` (an already-onboarded **ESPN** league
the caller isn't a member of yet). On `200` for a **non-owner** the flow routes straight to the
dashboard rather than attempting a refresh (refresh is owner-only, so a refresh attempt would
`403`); the owner path still re-onboards/refreshes.

**Joining vs. onboarding are distinct UIs.** A non-member doesn't use the onboard/refresh form
to "join": the **Join League** dialog (`join-league-dialog.tsx`) handles ESPN membership
verification only (`POST /leagues/{id}/verify-membership` — no onboard/refresh request) with
ESPN cookies (extension autofill or manual entry), then opens the dashboard. The landing-page
inline form opens this dialog on an ESPN `403` (the user has only entered a league ID there). On
the `/connect_league` page itself a `403` is handled inline using the cookies already entered on
the form (so the user isn't re-prompted), as a safety net for direct navigation.

## Scope
- Route: `/connect_league` (protected) (`src/app/app.tsx`).
- Component: `src/features/connect_league/league-connect.tsx`; schema
  `league-connect-schema.ts`; API in `api-calls.ts`.
- **Join League dialog:** `src/features/connect_league/join-league-dialog.tsx` (ESPN membership
  verification), opened from the landing-page inline connect form (FE-001) on a `403`.
- Triggers [BE-001](../backend/BE-001-league-onboarding.md) /
  [BE-002](../backend/BE-002-league-refresh.md); polls
  [BE-008](../backend/BE-008-job-status-tracking.md).

## Edge Cases
- **Private ESPN league:** requires `espn_s2` + `SWID`; cookies are transmitted once over
  HTTPS and cleared (`clearEspnCookies`) on success — never persisted or logged.
- **Chrome extension auto-fill:** ESPN cookies may be auto-filled by the extension
  ([EXT-001](../extension/EXT-001-espn-cookie-autofill.md)); the form must also accept
  manual entry. When the extension is detected the "Autofill cookies from ESPN" button is
  shown; when it is not detected, an inline hyperlink to the Chrome Web Store listing is
  shown instead so users can install it. The same behavior applies in the Join League dialog.
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
- **Non-owner of an existing league:** when the league already exists and the caller is not
  its owner, the flow opens the dashboard without sending an (owner-only) refresh; for ESPN it
  first verifies membership (a `403` on the lookup) before opening.
- **ESPN non-member join:** an ESPN `403` is a membership problem, not an onboard one — from
  the landing form it opens the Join League dialog (cookie autofill or manual entry →
  `verify-membership` → open the dashboard); on the connect page it verifies inline with the
  already-entered cookies. ESPN-rejected cookies surface the failure inline.
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
- [ ] A non-owner opening an already-onboarded league is routed to the dashboard without an
      onboard/refresh request; an ESPN non-member verifies membership first.
- [ ] ESPN credentials never appear in logs or persistent storage.

## Sources
`src/features/connect_league/`, `src/app/app.tsx`.
