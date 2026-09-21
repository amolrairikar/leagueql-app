## Why

When a user revokes Yahoo OAuth access but their Yahoo league is already onboarded, then
tries to connect that league, the app shows "Something went wrong — We couldn't complete your
Yahoo connection. Please try again." instead of taking them into their league.

The Yahoo connect entry (`landing-page.tsx`) always redirects to Yahoo's consent screen
first, so the revoked link is re-linked automatically and a fresh token is stored server-side.
On the OAuth return, `YahooConnectReturn` resumes onboarding via `POST /leagues?requestType=ONBOARD`.
Because the league already exists, the backend returns `200 {"detail":"League already
onboarded","data":null}` (`src/api/routes.py`). Since it's a 200 the client does not throw,
and the return handler blindly reads `result.data.correlation_id`, throwing a `TypeError` on
the null `data`. That is caught by the generic handler and rendered as the "Something went
wrong" error — instead of routing the user into their existing league.

## What Changes

- On the Yahoo OAuth return, an already-onboarded league (the `200`/`data:null` "League
  already onboarded" response) SHALL skip job polling and route the user straight into their
  existing league dashboard, mirroring the successful-onboard path — instead of surfacing a
  generic error. This matches how the ESPN/Sleeper connect form already opens an existing
  league.

## Capabilities

### New Capabilities
<!-- none -->

### Modified Capabilities
- `frontend/connect-yahoo-league`: The "Handle the OAuth return" requirement gains a scenario
  for an already-onboarded league, so the return leg routes to the existing dashboard rather
  than erroring.

## Impact

- **Code:** `frontend/src/features/connect_league/yahoo-connect-return.tsx` (guard polling on
  a null `data` and fall through to the existing route-to-league path),
  `frontend/src/features/connect_league/api-calls.ts` (`onboardYahooLeague` return type allows
  `data: null`).
- **Reuse:** the existing success path (`clearApiCache` → `getLeague` → `setLeagueCookies` →
  `navigate('/home')`) already present in the same effect.
- **Tests:** a jest-cucumber scenario in the `connect_league` `__tests__` Yahoo pair for the
  already-onboarded return.
- **Specs:** `openspec/specs/frontend/connect-yahoo-league/spec.md`.
