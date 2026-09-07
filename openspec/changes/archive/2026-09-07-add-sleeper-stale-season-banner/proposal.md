## Why

Sleeper links a league's seasons backward-only (each season's league is reached from the next
via `previous_league_id`), so once a new NFL season starts, a league onboarded for a prior
season can never discover the new season by refreshing — the owner must onboard the **new
season's** league ID from scratch. The backend's scheduled auto-refresh already encodes this
(it skips any Sleeper league whose newest onboarded season is behind the current NFL season,
`src/sleeper_refresh/utils.py`), but nothing surfaces the situation to the user, who just sees
stale data with no explanation.

## What Changes

- A new thin banner renders below the in-app header on every main-app page, but only for a
  **Sleeper** league, only for the league **owner**, and only when the current fantasy season is
  after the league's latest onboarded season. It reads: *Not seeing your current season's data?
  Enter your latest season's league ID on the landing page.* with "landing page" linking to `/`.
- The current fantasy season is computed locally from the browser clock — the calendar year,
  minus one before September (the NFL season flips in September). No network call is needed:
  the league's onboarded seasons are already available client-side from `getLeagueCookies()`.
- The banner is not dismissible — it disappears on its own once a current-season league is
  onboarded. It does not render for ESPN leagues, in demo mode, for non-owners, when no league
  is connected, when the league has no seasons, or while ownership is still loading.

## Capabilities

### New Capabilities
- `frontend/sleeper-stale-season-banner`: An owner-only, Sleeper-only banner that tells the owner
  to onboard the current season's league ID when their latest onboarded season is behind the
  current fantasy season.

## Impact

- Frontend: new banner component + season-staleness hook under `frontend/src/features/sidebar/`,
  wired into `AppLayout` (`frontend/src/app/app.tsx`). Reuses `useIsOwner`
  (`frontend/src/features/ownership/use-is-owner.ts`) and `getLeagueCookies`/`isDemoMode`
  (`frontend/src/lib/cookie-handler.ts`). No backend or API changes.
- Tests: a new frontend component test (jest-cucumber) under
  `frontend/src/features/sidebar/__tests__/`.
