# Design

## Context

See proposal.md for motivation. Current state:

- `get_leagues_to_refresh` (`src/league_refresh/utils.py`) handles Yahoo and ESPN in one
  "credentialed, opt-in" branch: it reads `owner_user_id` + `auto_refresh_enabled` from each
  canonical league's `METADATA` and skips the league unless both are present/true.
- The landing page holds a `yahooAutoRefresh` checkbox state, stashes it in sessionStorage
  (`yahoo-auto-refresh-pref.ts`) before the consent popup/redirect, and passes it to
  `onboardYahooLeague(leagueId, autoRefresh)` on both the in-place and return legs.
- The onboarder persists whatever `autoRefresh` the request carries as `auto_refresh_enabled` on
  `METADATA` (backend/league-onboarding), for any platform.
- `PUT /leagues/{id}/auto-refresh` accepts any platform; nothing in the UI calls it for Yahoo.

## Goals / Non-Goals

**Goals:**
- Every in-season Yahoo league with an owner is refreshed by the scheduled run.
- The Yahoo connect UI stops presenting a choice that no longer exists.

**Non-Goals:**
- Adding a manual Refresh League action for Yahoo.
- Changing ESPN's opt-in, cookie storage, Refresh League dialog, or Turn Off Auto-Refresh.
- Changing the onboard API contract, `PUT /leagues/{id}/auto-refresh`, or the onboarder's
  persistence of `auto_refresh_enabled`.
- Cleaning up existing `auto_refresh_enabled` values on Yahoo `METADATA` items.
- Surfacing a failed scheduled Yahoo refresh (revoked/expired token) to the owner.

## Decisions

**1. Ignore the flag for Yahoo in selection, rather than backfilling it to true.**
Split the combined Yahoo/ESPN branch so Yahoo requires only `owner_user_id` and ESPN keeps
requiring `auto_refresh_enabled`. `_get_refresh_metadata` still returns both values; Yahoo just
doesn't check the flag.
- *Alternative — backfill `auto_refresh_enabled = true` on existing Yahoo leagues and default new
  Yahoo onboards to true:* needs a one-off migration script, and leaves a stored flag that could
  still be flipped off (API, stale client) and silently freeze a league again. Ignoring the flag
  removes that failure mode entirely.
- *Alternative — treat Yahoo exactly like Sleeper (no METADATA read):* not possible; the onboarder
  needs `owner_user_id` to load the owner's Yahoo token, so the METADATA read stays.

**2. Leave the backend write path and `PUT /auto-refresh` untouched.**
After this change the frontend omits `autoRefresh` for Yahoo onboards, and the onboarder keeps
persisting whatever an ESPN/Yahoo request carries. A stored Yahoo `auto_refresh_enabled` becomes an
inert value. Rejecting Yahoo in `PUT /auto-refresh` or in the onboarder would add API surface
changes (and an OpenAPI/contract change) for no user-visible benefit, since no UI sends them.
Documentation (`docs/db/dynamodb_spec.md`, `docs/api/openapi_spec.yaml`) is updated to say the flag
only governs ESPN selection.

**3. Frontend: remove the checkbox and the sessionStorage pref helper entirely.**
Drop the `yahooAutoRefresh` state, the checkbox + tooltip, `setYahooAutoRefreshPref` /
`takeYahooAutoRefreshPref` and their module, and the `autoRefreshOverride` parameter on
`handleYahooConnect`. Call `onboardYahooLeague(leagueId)` without an opt-in, and make the helper
omit `autoRefresh` from the Yahoo request body rather than sending `false`. Nothing replaces
the checkbox: an earlier draft added an always-on refresh note, which was dropped at review.
- *Alternative — keep the checkbox but default it on / disable it:* a control that can't be changed
  is noise.
- A stale `leagueql:yahoo-auto-refresh` key left in a user's sessionStorage by an older build is
  harmless: nothing reads it, and sessionStorage is tab-scoped and short-lived.

## Risks / Trade-offs

- [More Yahoo API load per weekly run (previously opted-out leagues now refresh)] → Existing
  per-platform dispatch pacing (base interval + jitter) already staggers Yahoo onboarders; Yahoo
  league count is small today. Watch onboarder error rates on the first in-season run.
- [Owners whose Yahoo token is revoked/expired now generate failed scheduled refresh jobs] → Same
  behavior opted-in leagues already have (the onboarder fails the job with `YAHOO_AUTH`); the
  per-league failure isolation in the refresher keeps other leagues unaffected. Surfacing this to
  the owner is out of scope.
- [Owners who deliberately left the box unchecked now get refreshed] → Acceptable: refreshing only
  reads data they already authorized LeagueQL to read, and the Privacy Policy already covers it.

## Migration Plan

1. Deploy backend (refresher selection change) and frontend independently — neither depends on the
   other. Old frontends sending `autoRefresh` for Yahoo are harmless since the flag is ignored.
2. The next in-season scheduled run picks up all owned Yahoo leagues; no data migration.
3. Rollback: revert the refresher change to restore flag-gated selection (Yahoo leagues onboarded
   after the frontend change would have `auto_refresh_enabled` false/absent and stop refreshing, so
   roll back the frontend too if the backend is reverted).
