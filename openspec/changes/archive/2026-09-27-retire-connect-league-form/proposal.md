## Why

After ESPN/Sleeper onboarding moved inline to the landing page and ESPN refresh moved to an
in-dashboard dialog (change `espn-inline-onboarding`), the standalone `/connect_league`
ESPN/Sleeper onboard/refresh form (`LeagueConnectForm`) is no longer part of any primary flow —
it is only reachable via two "View another league" fallback buttons. Keeping it is dead-weight
UI that duplicates the landing page. The one capability that still lived only on that form —
enabling automatic weekly refresh for an already-onboarded ESPN league — must be preserved, so we
add its opt-in to the Refresh League dialog before removing the form.

## What Changes

- Add an "enable automatic weekly refresh" opt-in checkbox (with the explanatory tooltip) to the
  in-dashboard **Refresh League dialog**, defaulting off. Checking it sends the opt-in with the
  `POST /leagues` refresh so an already-onboarded ESPN league can enroll in auto-refresh.
- Repoint the two "View another league" buttons (`ownership/membership-guard.tsx`,
  `connect_league/join-invite-page.tsx`) from `/connect_league` to the landing connect entry
  `/?connect=true` (matching the sidebar's "View Another League").
- **Remove** the ESPN/Sleeper `LeagueConnectForm` and its zod schema (`league-connect-schema.ts`).
  The `/connect_league` route stays but now only serves the **Yahoo OAuth return**
  (`YahooConnectReturn`); any other hit redirects to `/?connect=true`.
- Remove the now-obsolete form component tests
  (`connect_league/__tests__/connect-league.{feature,steps.test.tsx}`); the equivalent behavior is
  covered by the landing-page and refresh-dialog tests.

## Capabilities

### New Capabilities
<!-- None -->

### Modified Capabilities
- `frontend/connect-league`: the onboard/refresh no longer has a standalone form with locked
  pre-filled fields; the ESPN auto-refresh opt-in now lives on the landing-page onboard and the
  Refresh League dialog rather than a dedicated form.
- `frontend/navigation-sidebar`: the Refresh League dialog gains the "enable automatic weekly
  refresh" opt-in checkbox so an already-onboarded ESPN league can enroll from the dialog.

## Impact

- Frontend: `frontend/src/features/sidebar/refresh-league-dialog.tsx` (add opt-in),
  `frontend/src/features/connect_league/league-connect.tsx` (reduce to the Yahoo-return
  dispatcher), delete `frontend/src/features/connect_league/league-connect-schema.ts`,
  repoint buttons in `frontend/src/features/ownership/membership-guard.tsx` and
  `frontend/src/features/connect_league/join-invite-page.tsx`.
- Tests: delete `connect_league/__tests__/connect-league.*`; extend
  `sidebar/__tests__/refresh-league.*` for the opt-in.
- Docs: `frontend/src/features/instructions/instructions-page.tsx` auto-refresh opt-in wording.
- No backend, API-contract, or extension changes. The `/connect_league` route remains for Yahoo.
