## Why

ESPN league data can only be refreshed manually once per week, but nothing tells the owner
when their data has gone stale — they have to notice on their own. A lightweight reminder that
appears once the data is more than 7 days old (exactly when the refresh cooldown expires) nudges
owners to refresh at the moment it is both worthwhile and permitted.

## What Changes

- `GET /leagues/{leagueId}` returns two additional fields in its `200` payload: `last_refresh_at`
  (nullable ISO 8601 — absent until the first REFRESH) and `onboarded_at` (ISO 8601). This lets
  the frontend compute data freshness as `last_refresh_at ?? onboarded_at`.
- A new thin banner renders below the in-app header on every main-app page, but only for an
  **ESPN** league, only for the league **owner**, and only when the league's data is more than
  7 days old. It reads: *Refresh your ESPN league data by clicking the "Refresh League" button
  in the sidebar!*
- The banner is not dismissible — it disappears on its own once the league is refreshed. It does
  not render for Sleeper leagues (they auto-refresh), in demo mode, for non-owners, or while the
  league's freshness is still loading.

## Capabilities

### New Capabilities
- `frontend/refresh-reminder-banner`: An owner-only, ESPN-only banner that reminds the owner to
  refresh their league when its data is more than 7 days old.

### Modified Capabilities
- `backend/league-metadata`: `GET /leagues/{leagueId}` additionally returns `last_refresh_at`
  and `onboarded_at` so the frontend can determine data freshness.

## Impact

- Backend: `src/api/routes.py` (`get_league` response), `docs/api/openapi_spec.yaml`
  (`LeagueFoundData` schema + example). No DynamoDB schema change — both fields already exist on
  the `METADATA` item.
- Frontend: new banner component + freshness hook under `frontend/src/features/sidebar/`, wired
  into `AppLayout` (`frontend/src/app/app.tsx`); `GetLeagueResponse` type
  (`frontend/src/components/api/types.ts`) and the demo mirror (`frontend/src/lib/demo-api.ts`).
- Tests: backend unit (`tests/unit/api`), backend component (`tests/component`) if the response
  shape is asserted there, and a new frontend component test under
  `frontend/src/features/sidebar/__tests__/`.
