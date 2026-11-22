# Proposal

## Why

Connecting an already-onboarded Yahoo league as a signed-in user who is **not** that league's owner or a member fails confusingly. `POST /leagues` returns `200 "already onboarded"`, then `GET /leagues/{id}` returns `403` (`require_league_member`). `handleYahooConnect` (`frontend/src/features/landing_page/use-landing-page.tsx`) catches *any* `403` as "Yahoo not linked" and opens the Yahoo consent popup. The Yahoo account is already linked, so the popup flashes (`about:blank`) and closes at once; its `postMessage` re-runs `handleYahooConnect`, which hits the same `403`, and the cycle repeats until a generic "Something went wrong" error. Prod API Gateway access logs confirm it: repeated `GET /leagues/{id}` `403` responses from a Clerk account that is not the league's owner. The user sees no hint that the real fix is an invite link from the league owner.

## What Changes

- Distinguish the source of a `403` in the Yahoo connect flow: only a `403` from `POST /leagues` ("Link your Yahoo account first") or a `YAHOO_AUTH` job failure starts the Yahoo OAuth step.
- A `403` from `GET /leagues/{id}` after onboarding SHALL show an inline not-a-member message (ask the league owner for an invite link), via the shared `ErrorAlert`, stop the loading state, and never open the consent popup — matching the existing ESPN member-gate message.
- Bound the consent retry: after one consent round-trip has completed (popup `postMessage` or full-page return), a further "link first"/`YAHOO_AUTH` signal shows an inline error instead of reopening consent, so no unbounded popup loop is possible.
- Frontend only. The migrate-league flow was checked and is unaffected (its `403` comes from `yahoo_members`, which only means "link first"); no backend, API, or infra changes.

## Capabilities

### New Capabilities
<!-- None. -->

### Modified Capabilities
- `frontend/connect-yahoo-league`: adds requirements for the not-a-member outcome and the bounded consent retry.
- `frontend/landing-page`: the "Resume the Yahoo OAuth return inline" requirement no longer restarts consent when a signal follows a completed consent; it shows an inline error.

## Impact

- `frontend/src/features/landing_page/use-landing-page.tsx` (`handleYahooConnect`, `startYahooOauth`, return-resume effect, popup message handler).
- Frontend component tests: `frontend/src/features/landing_page/__tests__/landing-connect.feature` and `landing-connect.steps.test.tsx` (MSW-mocked).
- `openspec/specs/frontend/connect-yahoo-league` and `frontend/landing-page` (via archive).
- No backend/OpenAPI/DynamoDB/architecture-diagram changes; no backend tests (behavior of `require_league_member` is unchanged).
