## Context

See `proposal.md` — Why. The `/connect_league` route dispatches in
`frontend/src/features/connect_league/league-connect.tsx`: `platform=YAHOO` renders
`YahooConnectReturn` (the Yahoo OAuth return leg), otherwise it renders `LeagueConnectForm` (the
ESPN/Sleeper onboard/refresh form). Only the Yahoo branch is still reached by a real flow; the form
is reached solely by two "View another league" fallback buttons. `EspnCredentialFields` and the
Refresh League dialog already exist from the prior change.

## Goals / Non-Goals

**Goals:**
- Remove the redundant ESPN/Sleeper form without losing any capability.
- Preserve mid-life auto-refresh opt-in by adding it to the Refresh League dialog.
- Keep the `/connect_league` route working for the Yahoo OAuth return.

**Non-Goals:**
- No backend/API/extension changes.
- Not touching the Yahoo return, landing-page onboard, or Sleeper flows beyond the button repoint.

## Decisions

- **Keep the route, drop the form.** `LeagueConnect` is reduced to: render `YahooConnectReturn`
  for `platform=YAHOO`, otherwise `<Navigate to="/?connect=true" replace />`. This preserves the
  Yahoo callback target and turns any stray hit into the canonical connect entry, so no dead form
  is shipped. Alternative (delete the route entirely) would break the Yahoo OAuth return.
- **Opt-in moves to the Refresh League dialog**, defaulting off. The manual-refresh action only
  appears for a not-enrolled league, so a simple unchecked-by-default checkbox is correct — no
  need to pre-read enrollment. The dialog sends `autoRefresh` from the checkbox instead of the
  hardcoded `false`.
- **Repoint the two "View another league" buttons to `/?connect=true`** (the landing connect
  entry the sidebar already uses) rather than relying on the route's redirect, so the buttons are
  self-evidently correct.
- **Delete the form's component tests** (`connect-league.{feature,steps.test.tsx}`); their
  behaviors are covered by the landing-page tests (onboard, non-member invite) and the
  refresh-dialog tests (refresh, cooldown, opt-in). Delete `league-connect-schema.ts`, which only
  the form used.

## Risks / Trade-offs

- **Lost test coverage for the retired form** → mitigated: onboarding/refresh/opt-in behaviors are
  exercised by `landing-connect` and `refresh-league` tests; the removed tests only covered the
  form UI that no longer exists.
- **A bookmarked `/connect_league?platform=espn` URL** → now redirects to `/?connect=true` instead
  of showing a form; acceptable, since that entry is the supported path.
- **Yahoo return regression risk** → the Yahoo branch of `LeagueConnect` and `YahooConnectReturn`
  are untouched; the existing `yahoo-connect` tests still render `/connect_league?platform=YAHOO`.
