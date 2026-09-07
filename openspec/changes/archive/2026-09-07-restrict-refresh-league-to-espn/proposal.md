## Why

Sleeper leagues refresh on their own: a scheduled job runs weekly during the season
(`backend/scheduled-sleeper-auto-refresh`), and a new season is picked up by onboarding the new
season's league ID rather than by refreshing. There is nothing for a Sleeper owner to do with a
"Refresh League" action, so showing it in the sidebar is misleading — it implies a manual step
that does not exist for Sleeper. The action is only meaningful for ESPN, whose data is refreshed
by re-submitting credentials.

## What Changes

- The sidebar's owner-only **Refresh League** action is now shown only for **ESPN** leagues,
  matching how **Invite Leaguemates** is already gated. Sleeper owners no longer see it. Migrate,
  Transfer Ownership, and Delete remain owner-only for both platforms.
- The user docs are updated so every reference to "Refresh League" as a sidebar action is marked
  **ESPN only**: the owner-actions list in "League Ownership" tags it `(ESPN only)` (alongside the
  existing `Invite Leaguemates (ESPN only)`). The "Refreshing League Data" section already splits
  ESPN and Sleeper, and the ESPN-form references ("Onboard/Refresh League" form) are already
  ESPN-scoped, so those stay as-is.

## Impact

- Frontend: `frontend/src/features/sidebar/app-sidebar.tsx` (gate the Refresh League item on
  `platform === 'ESPN'`); docs copy in `frontend/src/features/instructions/instructions-page.tsx`.
- Tests: `frontend/src/features/sidebar/__tests__/ownership-gating.*` (the owner scenario used a
  Sleeper league and asserted Refresh League — switch it to ESPN) plus a new scenario covering
  that a Sleeper owner does not see Refresh League. No backend or API changes.
