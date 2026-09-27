# Design

## Context

See proposal.md — Why. Today the already-linked Yahoo onboard already runs inline on the landing page
via `handleYahooConnect` (`onboardYahooLeague` → `pollForCompletion` → `getLeague`/`setLeagueCookies`
→ `/home`), driving the same time-based `Progress` bar as ESPN/Sleeper. The only non-inline leg is the
OAuth consent round-trip: the backend callback (`src/api/routes.py`) 302s the browser to the frontend
base chosen by the state's `flow`, currently `main.YAHOO_CONNECT_RETURN_URL` for `ONBOARD`, and
appends `?platform=YAHOO&yahooLinked=1|0&leagueId=<id>`. The landing page currently reads only
`?connect=true` on mount. Return params are handled by `YahooConnectReturn` on the `/connect_league`
route (a `ProtectedRoute`).

## Goals / Non-Goals

**Goals:**
- The Yahoo OAuth return resolves inline on `/` with the hero progress bar, reusing the existing
  `handleYahooConnect` chain (no duplicate onboarding logic).
- No broken window across deploys, regardless of which tier ships first.

**Non-Goals:**
- The `/migrate_league` OAuth return (unchanged).
- Any change to the backend OAuth handshake, token storage, or the callback's param-appending logic —
  only the configured `ONBOARD` return base changes.

## Decisions

- **Return base = landing root `/`, callback logic untouched.** The callback already appends the
  return params to a configured base, so pointing `YAHOO_CONNECT_RETURN_URL` at `https://leagueql.app/`
  yields `/?platform=YAHOO&yahooLinked=1&leagueId=<id>` with no code change in `routes.py`. Alternative
  (a dedicated `/yahoo/return` route) rejected: it reintroduces a separate page, the opposite of the
  goal.
- **Reuse `handleYahooConnect` for the return resume.** It already onboards + polls + routes and
  already restarts OAuth on `403`/`YAHOO_AUTH`, so revoked-link recovery is free. Refactor it to accept
  an optional `autoRefresh` override so the return path can pass `takeYahooAutoRefreshPref()` (the
  sessionStorage opt-in stashed before the redirect) instead of the checkbox state; the normal submit
  path keeps using the checkbox default. Alternative (porting `YahooConnectReturn`'s effect verbatim
  into the landing page) rejected: it would duplicate the onboard/poll logic.
- **Mount effect keyed on `isSignedIn`, guarded by a `startedRef`.** Mirrors the existing
  `?connect=true` effect. The OAuth caller is already signed in (Clerk session persists across the
  redirect), and the effect must wait for `isSignedIn` to resolve; the ref prevents a StrictMode
  double-run (same guard `YahooConnectReturn` used). After handling, strip the params with
  `history.replaceState` so a reload does not re-onboard.
- **`/connect_league` → redirect shim.** `league-connect.tsx` forwards Yahoo return params to `/`
  (`<Navigate to={/?<params>} replace />`) and keeps the existing non-Yahoo `→ /?connect=true`
  fallback; `yahoo-connect-return.tsx` is deleted. This keeps in-flight OAuth and stale bookmarks
  working during/after the transition without a second onboarding code path.

## Risks / Trade-offs

- **Deploy ordering** → Ship frontend first (landing handles the new params; the `/connect_league`
  shim forwards them), then flip the backend return URL. If frontend leads, old callbacks still land on
  `/connect_league` and are forwarded to `/`; reverse order would briefly drop returns on a landing
  page that can't yet parse them. (cf. the OTel traceparent/CORS ordering lesson.)
- **Signed-out on return (edge)** → The visitor should still be signed in; the effect gates on
  `isSignedIn` like the `?connect=true` path, so if the session is somehow gone the params are simply
  ignored (no crash) and the marketing page renders.
- **Landing `/` is public, `/connect_league` was `ProtectedRoute`** → Fine: the resume calls
  Clerk-authenticated APIs only after `isSignedIn` resolves; unauthenticated loads just render
  marketing.

## Migration Plan

1. Deploy frontend (landing return handling + `/connect_league` shim + `YahooConnectReturn` removed).
2. Flip backend `YAHOO_CONNECT_RETURN_URL` / Terraform `yahoo_connect_return_url` to the landing root
   and deploy.
3. Rollback: revert the env var to `.../connect_league`; the shim still forwards, so returns keep
   working even mid-rollback.
