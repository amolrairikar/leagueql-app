# Proposal

## Why

ESPN, Sleeper, and already-linked Yahoo leagues all onboard inline on the landing-page hero with a
progress bar, but a first-time (unlinked) Yahoo user is sent through Yahoo's consent screen and
returned to a *separate* `/connect_league` page with a plain spinner — a jarring, inconsistent
experience. Routing the OAuth return back to the landing page gives Yahoo users one continuous inline
flow like ESPN.

## What Changes

- The ONBOARD-flow Yahoo OAuth callback returns the browser to the landing page (`/`) instead of the
  standalone `/connect_league` page.
- The landing page detects the Yahoo return params (`platform=YAHOO&yahooLinked=…&leagueId=…`) on
  load, auto-opens the connect form, and resumes onboarding inline with the hero progress bar,
  reusing the existing already-linked onboard chain. A declined/failed link (`yahooLinked=0`) shows an
  inline retry alert with Yahoo preselected.
- `/connect_league` becomes a redirect shim that forwards any Yahoo return params to `/`; the
  `YahooConnectReturn` component is removed.
- The Yahoo consent handshake runs in a **popup window** instead of a full-page redirect, so the
  connect page stays mounted (progress bar keeps running) and onboarding resumes with no page
  reload. The callback returns a `postMessage` page for the popup, and the app falls back to the
  full-page redirect when the browser blocks the popup.
- The Yahoo migrate flow (`/migrate_league`) is unchanged.

## Capabilities

### New Capabilities

_None._

### Modified Capabilities

- `frontend/landing-page`: the inline connect flow gains handling of the Yahoo OAuth return params on
  page load (resume onboarding inline on `yahooLinked=1`; inline retry alert on `yahooLinked=0`).
- `frontend/connect-yahoo-league`: the "Handle the OAuth return" requirement moves the return target
  from `/connect_league` to the landing page `/` and resolves it inline with the hero progress UI.
- `backend/yahoo-oauth`: the ONBOARD-flow callback return URL points at the landing-page base
  (`https://leagueql.app/`) rather than `/connect_league`; the MIGRATE-flow return is unchanged.

## Impact

- **Frontend:** `frontend/src/features/landing_page/landing-page.tsx` (return-param mount effect;
  `handleYahooConnect` gains an optional auto-refresh override; `startYahooOauth` opens a popup and
  resumes on its `postMessage`, with redirect fallback), `frontend/src/features/connect_league/api-calls.ts`
  (`getYahooAuthorizeUrl` gains `display`), `frontend/src/features/connect_league/league-connect.tsx`
  (redirect shim); delete `frontend/src/features/connect_league/yahoo-connect-return.tsx`. Tests:
  `landing_page/__tests__/landing-connect.*` (return + popup scenarios) and
  `connect_league/__tests__/yahoo-connect.*` (removed/migrated).
- **Backend:** `src/api/main.py` `YAHOO_CONNECT_RETURN_URL` default; `infrastructure/regional/vars.tf`
  `yahoo_connect_return_url` default. `src/api/routes.py` gains a `display` param on the authorize
  route and a popup `postMessage` HTML response (nonce-CSP) on the callback; `src/api/yahoo_oauth.py`
  carries `display` in the OAuth state.
- **Deploy order:** ship frontend first (landing handles the params; `/connect_league` shim forwards
  them), then flip the backend return URL — avoids a broken window regardless of tier order.
