# Design

## Context

- `onboard_league` checks four "blocked" conditions in order and raises straight away: in progress
  (409), weekly cooldown (429, outside dev), NFL offseason (409) and already up to date (409).
- ESPN cookies are stored and `auto_refresh_enabled` is set only by the onboarder, after an
  opted-in fetch succeeds. That fetch is also what proves the cookies work.
- The API Lambda already holds the shared credential KMS key with Encrypt/Decrypt (it encrypts
  Yahoo tokens), and `src/api/espn_credentials.py` already wraps the shared engine for deletes.

## Decisions

- **Enroll in the API, not by invoking the onboarder.** A blocked refresh must not run the data
  pipeline, so the API does the opt-in work itself and keeps the block response unchanged.
- **Validate before storing.** Without the onboarder's fetch, bad cookies would be stored silently
  and only fail at the next scheduled refresh. A single `mTeam` read (the members proxy's call,
  now shared as `_fetch_espn_league_teams`) checks them. `401`/`403` → `400` (actionable), other
  failures → `502`. A public league accepts any cookies, which matches the onboarder.
- **All benign blocks enroll**: cooldown, offseason, up to date and in progress. Each means "data
  can't refresh now", and none of them is a reason to drop the opt-in.
- **Keep the original status code.** The frontend already treats `409`/`429` as benign, and it
  knows it sent the opt-in. Because enrollment failures surface as `500`, an opted-in `409`/`429`
  always means "enrolled", so no new response shape is needed.
- **Store the cookies, then set the flag.** If the flag write fails after storing, the cookies are
  orphaned but harmless (the next store replaces them). The reverse order could leave an enrolled
  league with no cookies, which would fail its next scheduled refresh.
- **The owner check runs first.** Enrollment happens after `require_league_owner`, so only the
  owner can enroll.

## Risks

- ESPN latency adds up to 10s (the request timeout) to a blocked opted-in request. That's
  acceptable for an explicit user action.
