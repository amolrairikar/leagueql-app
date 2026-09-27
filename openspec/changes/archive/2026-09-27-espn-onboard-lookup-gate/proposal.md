## Why

On the landing-page inline connect form, selecting ESPN immediately shows the SWID / espn_s2
credential inputs, the cookie helper, and the auto-refresh checkbox — before we know whether the
league even needs onboarding. A user whose league is already onboarded is still confronted with
a credential form they should never fill: membership now comes from an owner-shared invite link,
not by re-entering cookies. We should look the league up first and only ask for credentials when
the league genuinely isn't onboarded yet.

## What Changes

- ESPN credential inputs, the cookie helper, and the auto-refresh opt-in checkbox are **no longer
  shown on ESPN selection**. They are revealed only after a Connect submit whose `getLeague`
  existence check returns `404` (not onboarded).
- The single **Connect** button is kept. The first click runs the lookup: `404` reveals the
  credential fields (and sends no `POST /leagues`); a second click, with SWID/espn_s2 filled in,
  onboards in place exactly as today.
- An ESPN `403` (onboarded, caller not a member) now surfaces the copy: *"League already
  onboarded. Please reach out to your leaguemate who onboarded the league to get your
  league-specific invite link."* A `200` (caller is a member/owner) still routes into the
  existing dashboard.
- Scope is ESPN only. Sleeper and Yahoo inline flows are unchanged.
- No backend, API-contract, DynamoDB, extension, or infrastructure changes — `GET /leagues/{id}`
  already returns `200` / `403` / `404`.

## Capabilities

### New Capabilities
<!-- None -->

### Modified Capabilities
- `frontend/landing-page`: the inline-connect existence check now gates ESPN credential fields
  behind a `404` lookup result (hidden on ESPN selection, revealed on first `404`) and updates
  the `403` non-member copy to the "already onboarded / invite link" message.

## Impact

- Frontend: `frontend/src/features/landing_page/landing-page.tsx` (new `needsEspnCredentials`
  gate state, reveal-then-onboard `404` handling, updated `403` copy, reset on league-ID /
  platform change).
- Tests: `frontend/src/features/landing_page/__tests__/landing-connect.{feature,steps.test.tsx}`
  (credential fields hidden until `404`; first `404` reveals fields with no `POST`; two-click
  onboard; updated `403` copy). The `statefulGetLeague` MSW helper is adjusted to return `404`
  for both pre-onboard lookups, then `200` for the post-success read.
- No backend, API-contract, DynamoDB, extension, or infrastructure changes.
