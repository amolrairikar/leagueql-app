## Why

ESPN league owners can opt into scheduled auto-refresh (per-league `auto_refresh_enabled` flag on
the `METADATA` item), but there is **no way to opt back out** from the UI. Once enrolled, the
sidebar's manual **Refresh League** action and the reminder banner are hidden, leaving the owner
with no control to turn the schedule off.

The backend already fully supports opt-out — `PUT /leagues/{leagueId}/auto-refresh` with
`{ enabled: false }` clears the flag and, for the owner's last opted-in ESPN league, deletes their
stored ESPN cookies (backend/scheduled-league-auto-refresh, backend/espn-credential-storage). The
frontend client `setAutoRefresh(...)` exists but is never called. This change wires up the missing
UI.

It also reconciles the user docs and the in-app changelog, which already describe a "sidebar
Auto-Refresh toggle" that was never built.

## What Changes

- The sidebar gains a **Turn Off Auto-Refresh** owner action, shown only for ESPN leagues whose
  `auto_refresh_enabled` is true (the exact complement of the Refresh League action). It opens a
  confirmation dialog and calls `PUT /leagues/{leagueId}/auto-refresh` with `enabled=false`;
  on success the league is no longer enrolled and the manual Refresh League action returns.
- The `/docs` "Managing Your League" section is corrected: ESPN auto-refresh is turned off via the
  sidebar **Turn Off Auto-Refresh** action (which removes stored cookies), and the false claim that
  Yahoo has a sidebar toggle is dropped (Yahoo opt-in remains connect-time only). The owner-actions
  list marks **Turn Off Auto-Refresh** as ESPN only.
- The in-app changelog (`1.8.0`) wording is corrected to match what actually ships (content edit,
  not spec'd per release).

Scope is **ESPN only**; a Yahoo opt-out control is out of scope for this change.

## Capabilities

### Modified Capabilities
- `frontend/navigation-sidebar`: adds a Turn Off Auto-Refresh owner action gated on the league
  being an ESPN league enrolled in auto-refresh (`auto_refresh_enabled` true), plus its
  confirmation-dialog behavior.
- `frontend/instructions-docs`: documents disabling ESPN auto-refresh via the sidebar action and
  lists it as an ESPN-only owner action; corrects the Yahoo wording.

## Impact

- **Frontend:** new `features/sidebar/disable-auto-refresh-dialog.tsx`;
  `features/sidebar/app-sidebar.tsx`; `features/instructions/instructions-page.tsx`;
  `features/changelog/constants.ts`. Reuses the existing `setAutoRefresh` client and
  `useIsOwner().autoRefreshEnabled`.
- **Tests:** frontend component (vitest + jest-cucumber) for the sidebar suite and the docs page.
- No backend, API contract, data model, or infrastructure change (the endpoint already exists).
