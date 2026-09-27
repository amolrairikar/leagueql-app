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

- **Popup consent instead of a full-page redirect.** A redirect-based OAuth necessarily unloads and
  later reboots the SPA (a jarring mid-onboard reload). Instead `startYahooOauth` requests an
  authorize URL with `display=popup` and opens it with `window.open`; the connect page stays mounted
  with `loading` true so the progress bar keeps running. The callback, when the state records
  `display=popup`, returns a small HTML page whose script `postMessage`s
  `{ source: "yahoo-oauth", platform, yahooLinked, leagueId }` to the opener at the frontend origin
  and closes; the landing page listens for that message and resumes onboarding by reusing
  `handleYahooConnect`. Alternatives rejected: an iframe (providers send `X-Frame-Options: DENY` and
  interactive consent can't be framed) and "smooth the redirect" (any full-page redirect reboots the
  SPA — the reload can't be hidden).
  - **Popup-blocked fallback (single authorize URL).** If `window.open` returns null, the app
    navigates the current tab to the same authorize URL. The `display=popup` callback page detects it
    has no usable `window.opener` and self-redirects to the `page`-mode return URL, so onboarding
    still resumes inline via the existing mount effect — no second authorize call needed.
  - **Popup-dismissed detection.** A `setInterval` polling `popup.closed` (readable cross-origin)
    clears the loading state and shows a retry message if the user closes the window without
    finishing.
  - **Message-origin security.** The popup document is served by the **API** origin, so its
    `postMessage` arrives with `event.origin === <API origin>`; the listener verifies exactly that
    (derived from `API_BASE_URL`) and the message `source` tag before acting, and the callback targets
    the frontend's exact origin (never `*`).
  - **CSP for the inline script.** The API's security-headers middleware sets a strict
    `default-src 'none'` CSP via `setdefault`, which would block an inline script. The popup response
    sets its **own** CSP with a per-response nonce (`script-src 'nonce-…'`), so only that one script
    runs and everything else stays locked down.

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
