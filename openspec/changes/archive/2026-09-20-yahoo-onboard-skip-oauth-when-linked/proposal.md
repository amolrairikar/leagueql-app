# Proposal

## Why

A Yahoo user who has already linked their account (a stored Yahoo OAuth token
in DynamoDB) is still bounced through Yahoo's consent screen and the
"Onboarding your Yahoo league" OAuth-return page every time they connect a
league. That re-consent round-trip is pointless once linked — Sleeper users just
watch the progress bar and land on their league dashboard, and linked Yahoo
users should get the same experience.

## What Changes

- On the landing page, when a user selects Yahoo and clicks Connect, attempt an
  in-place onboard (`POST /leagues` with `platform=YAHOO`) **first**, instead of
  unconditionally redirecting to Yahoo's consent URL:
  - **Already linked** → onboard and poll to completion in place, showing the
    same Sleeper-style progress bar, then navigate to `/home`.
  - **Already onboarded** (the `200` null-`data` response) → route straight into
    the existing league dashboard, no polling.
  - **`YAHOO_AUTH` job failure** (a stored link whose refresh token was revoked)
    → redirect to the Yahoo OAuth (re)link step.
  - **`403` "Link your Yahoo account first"** (never linked) → fall back to the
    existing `GET /leagues/yahoo/oauth/authorize` full-page redirect. This is now
    the *only* path that shows the consent screen.
- No backend change: `POST /leagues` already 403-gates unlinked Yahoo callers
  before any side effect (`src/api/routes.py`), returns `200` with null `data`
  for an already-onboarded league, and surfaces `YAHOO_AUTH` on a revoked token.

## Capabilities

### New Capabilities
<!-- none -->

### Modified Capabilities
- `frontend/landing-page`: the inline connect routing gains a Yahoo branch — a
  Yahoo connect attempts an in-place onboard and only redirects to the OAuth
  consent screen when the caller has no stored Yahoo link.
- `frontend/connect-yahoo-league`: starting the OAuth link on Connect is no
  longer unconditional — an already-linked caller onboards in place; the consent
  redirect happens only for an unlinked (or revoked) caller.

## Impact

- Frontend only:
  - `frontend/src/features/landing_page/landing-page.tsx` — the `platform === 'YAHOO'`
    branch in `handleConnectSubmit`.
  - Reuses existing API helpers `onboardYahooLeague`, `getYahooAuthorizeUrl`,
    `pollForCompletion` (`frontend/src/features/connect_league/`).
  - Landing-page component tests (`landing-connect.feature` / `.steps.test.tsx`)
    gain linked-vs-unlinked Yahoo scenarios.
- No backend, API-contract, DynamoDB, or infrastructure changes.
