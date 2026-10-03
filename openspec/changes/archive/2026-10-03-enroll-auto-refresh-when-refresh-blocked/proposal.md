# Proposal

## Why

The sidebar Refresh League dialog lets an ESPN owner tick "Enable automatic weekly refresh". The
opt-in only takes effect inside the onboarder Lambda after a refresh succeeds: that is where the
cookies are stored and `auto_refresh_enabled` is set. When `POST /leagues?requestType=REFRESH` is
blocked, the onboarder never runs, so the opt-in is silently dropped. Blocked here means the weekly
cooldown (`429`), or a `409` because a refresh is in progress, the league is already up to date or
it's the NFL offseason. The owner sees "Refresh not available yet" and the league stays
unenrolled, even though they supplied valid cookies and asked for auto-refresh. A recent refresh
is the most common reason to open the dialog, so this is the case users hit most.

## What Changes

- On a blocked ESPN REFRESH that opts into auto-refresh and includes `swid`/`s2`, the API
  validates the cookies with a lightweight ESPN `mTeam` read. It then stores them encrypted and
  sets `auto_refresh_enabled = true` on the league's METADATA, and returns the original `409`/`429`
  unchanged.
- Cookies ESPN rejects (`401`/`403`) return `400`, and other ESPN failures return `502`. Nothing
  is stored or enrolled in either case. A storage or flag failure returns `500`, so a `409`/`429`
  for an opted-in request always means the league is enrolled. A missing season returns `400`.
- The dialog treats an opted-in `409`/`429` as "Automatic refresh enabled". It shows the backend
  message, clears the browser cookies, swaps the actions for a single **Done** button, and reloads
  on close so the sidebar shows Turn Off Auto-Refresh. A `400` shows the backend's cookie error.
- The ESPN `mTeam` fetch is shared between the members proxy and the new cookie check.

## Capabilities

- `backend/league-refresh`: a new requirement for enrolling an opted-in blocked refresh.
- `backend/espn-credential-storage`: storage on opt-in also covers a blocked, validated refresh.
- `frontend/navigation-sidebar`: the refresh dialog confirms enrollment on an opted-in block.

## Impact

- `src/api/routes.py`: `onboard_league` (block checks pulled out into `_refresh_block_reason`),
  `_enroll_blocked_espn_auto_refresh`, `_fetch_espn_league_teams`.
- `src/api/espn_credentials.py`: a `store_credentials` wrapper. The API role already has
  `kms:Encrypt` on the shared credential key, so no infrastructure change is needed.
- `frontend/src/features/sidebar/refresh-league-dialog.tsx`.
- `docs/api/openapi_spec.yaml`: `POST /leagues` documents the side effect plus `400`/`502`.
