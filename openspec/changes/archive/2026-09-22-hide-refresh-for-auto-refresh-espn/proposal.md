## Why

ESPN leagues can now opt into scheduled auto-refresh (per-league `auto_refresh_enabled` flag on
the `METADATA` item, surfaced as `auto_refresh_enabled` in the `GET /leagues/{id}` response). When
a league refreshes automatically on a schedule, the sidebar's manual **Refresh League** action —
and the reminder banner that points owners at it — are redundant and misleading. They should not be
shown for leagues that are enrolled in auto-refresh.

## What Changes

- The sidebar's **Refresh League** action is hidden for ESPN leagues whose `auto_refresh_enabled`
  is true (in addition to the existing owner + ESPN gating). It still shows for ESPN leagues that
  have not opted into auto-refresh.
- The **refresh-reminder banner** is likewise suppressed for auto-refresh-enabled ESPN leagues, so
  it never nudges an owner toward a button that is no longer shown.

## Capabilities

### Modified Capabilities
- `frontend/navigation-sidebar`: the Refresh League action is additionally gated on the league not
  being enrolled in auto-refresh (`auto_refresh_enabled` false/absent).
- `frontend/refresh-reminder-banner`: the reminder does not render for ESPN leagues enrolled in
  auto-refresh.

## Impact

- **Frontend:** `features/ownership/use-is-owner.ts` (expose `auto_refresh_enabled` from the
  `getLeague` fetch it already makes), `features/sidebar/app-sidebar.tsx`,
  `features/sidebar/refresh-reminder-banner.tsx`.
- **Tests:** frontend component (vitest + jest-cucumber) for the sidebar and banner suites.
- No backend, API contract, data model, or infrastructure change.
