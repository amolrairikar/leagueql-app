# FE-037: Connect Yahoo League (OAuth Account Linking)

## Description
Adds **Yahoo** as a selectable platform in the Connect League flow
([FE-002](FE-002-connect-league.md)). Because Yahoo requires OAuth 2.0 (unlike Sleeper's public
API or ESPN's cookie entry), onboarding a Yahoo league is a **two-step** experience: the user
first **links their Yahoo account** (OAuth consent), then selects/enters the Yahoo league to
onboard. The OAuth handshake and token storage are backend-owned
([BE-022](../backend/BE-022-yahoo-oauth.md)); this doc covers the UI.

**Link step.** When the user picks platform **Yahoo** and has no active link, the form replaces
the ESPN cookie fields with a **"Connect your Yahoo account"** button. Clicking it calls
`GET /auth/yahoo/authorize`, then navigates the browser to the returned Yahoo consent URL
(full-page redirect, not a stored-secret popup). After consent Yahoo returns to the backend
callback, which `302`-redirects back to `/connect_league?platform=YAHOO&yahooLinked=1`. On
return the form reads the `yahooLinked` marker, shows a linked/"Yahoo account connected" state,
and reveals the league-selection step.

**Onboard step.** Once linked, the user provides the Yahoo league to onboard and submits
`POST /leagues?requestType=ONBOARD` with `platform=YAHOO`. From there the flow is identical to
FE-002 — poll `GET /jobs/{jobId}` until `COMPLETED`/`FAILED`, surface the backend
`failure_reason`, clear the API cache, and route into the app on success.

Selecting a Yahoo league SHOULD be a **dropdown of the user's Yahoo leagues** (fetched from a
backend "my Yahoo leagues" listing that uses the stored token) rather than a raw ID field, since
Yahoo league keys (e.g. `nfl.l.123456`) are not user-facing; a manual league-key field is the
fallback if the listing is unavailable.

## Scope
- Route: `/connect_league` (protected) — extends the existing platform selector with `YAHOO`.
- Components: `src/features/connect_league/league-connect.tsx` (+ a Yahoo link sub-component,
  e.g. `yahoo-connect.tsx`), schema `league-connect-schema.ts`, API in `api-calls.ts`.
- New API calls: start OAuth (`GET /auth/yahoo/authorize`), read link status, list the user's
  Yahoo leagues (backend listing endpoint).
- Also surfaced from the landing-page inline connect form ([FE-001](FE-001-landing-page.md))
  when Yahoo is chosen there.
- Triggers [BE-001](../backend/BE-001-league-onboarding.md) (Yahoo branch) /
  [BE-002](../backend/BE-002-league-refresh.md); depends on
  [BE-022](../backend/BE-022-yahoo-oauth.md); polls
  [BE-008](../backend/BE-008-job-status-tracking.md).

## Edge Cases
- **Not linked yet:** choosing Yahoo shows the connect-account CTA and hides the league-selection
  step until a link exists; submit is disabled until linked.
- **Returning from OAuth (`yahooLinked=1`):** the form restores to the Yahoo platform, shows the
  linked state, and advances to league selection without a full re-entry. The marker query params
  are stripped from the URL after being read (no sticky linked banner on later visits).
- **Consent declined / linking failed:** the callback returns with a declined/failed marker; the
  UI shows an inline alert ("Yahoo linking was cancelled or failed — try again") with a retry
  CTA, not a hard error page. No global error banner (consistent with FE-002).
- **Link expired / revoked (`YAHOO_AUTH`):** when onboarding/refresh returns the backend
  re-link signal, the UI surfaces a "Reconnect your Yahoo account" prompt that restarts the OAuth
  step, rather than showing a generic failure.
- **League listing unavailable:** if the Yahoo-leagues listing fails, fall back to a manual
  league-key field with format guidance; a listing `401`/re-link signal routes to reconnect.
- **No leagues found:** if the linked Yahoo account has no fantasy football leagues, show an
  empty-state explaining the account has no eligible leagues (and offer to link a different
  account).
- **In-progress / slow job:** same ~120s polling contract as FE-002; show in-progress, success,
  and failure states with the backend message.
- **Owned vs. non-owned existing league:** same ownership handling as FE-002 — a non-owner
  opening an already-onboarded league routes to the dashboard without an owner-only refresh.
- **Pre-filled platform/league:** when arriving with a known Yahoo league, the platform/league
  fields are locked (as in FE-002); the link step still gates onboarding if unlinked.
- **Demo mode:** connecting (and the OAuth redirect) is disabled/redirected in demo mode.
- **No tokens in the browser:** the frontend never receives or stores Yahoo access/refresh
  tokens — it only observes link status via backend markers/endpoints (BE-022).

## Acceptance Criteria
- [ ] Selecting platform **Yahoo** while unlinked shows a "Connect your Yahoo account" CTA in
      place of the ESPN cookie fields, and disables onboard submit until linked.
- [ ] The CTA calls `GET /auth/yahoo/authorize` and navigates the browser to the returned Yahoo
      consent URL.
- [ ] Returning to `/connect_league?platform=YAHOO&yahooLinked=1` shows the linked state,
      reveals league selection, and strips the marker params from the URL.
- [ ] A declined/failed link shows an inline retry alert (no global banner, no hard error page).
- [ ] Once linked, the user selects a Yahoo league (dropdown of their leagues, or a manual
      league-key fallback) and onboards via `POST /leagues` with `platform=YAHOO`.
- [ ] The UI polls job status and shows in-progress, success, and failure states with the
      backend `failure_reason`, persisting through slow (~120s) jobs.
- [ ] A backend re-link signal (`YAHOO_AUTH`) surfaces a "Reconnect your Yahoo account" prompt
      that restarts the OAuth step.
- [ ] On success the user is routed into the app with the API cache cleared.
- [ ] Yahoo access/refresh tokens never appear in the frontend (no token in storage, state, or
      network responses).
- [ ] Connecting a Yahoo league is disabled/redirected in demo mode.

## Sources
`src/features/connect_league/`, `src/app/app.tsx`,
`docs/requirements/backend/BE-022-yahoo-oauth.md`.
