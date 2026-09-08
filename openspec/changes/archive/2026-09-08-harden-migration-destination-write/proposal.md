## Why

`POST /leagues/{leagueId}/migrate` writes the destination `LEAGUE_LOOKUP`
(`LEAGUE#{newPlatformLeagueId}#PLATFORM#{newPlatform}` → the caller's canonical league)
**synchronously in the API handler, before the onboarder runs**, after checking only that the
caller owns the *source* league and that the destination ID is not already onboarded. Nothing
verifies the caller can access the league on the *destination* platform, and there is no rollback
if the async onboarder later fails.

This lets an authenticated owner of any league register a destination `LEAGUE_LOOKUP` for an
arbitrary target-platform league ID they do not control (security finding **SEC-01**). The
legitimate owner of that ID is then blocked from onboarding (`lookup_league` returns "already
onboarded"), and the squatted mapping is owned by the attacker — an integrity/DoS attack on the
destination-platform namespace. The mapping persists even when the onboarder cannot fetch the
destination league (e.g. missing/invalid ESPN credentials).

Crucially, the API's up-front write is **redundant**: the onboarder's `writer.py` MIGRATE path
already writes the same destination `LEAGUE_LOOKUP` after it successfully fetches the destination
league. Removing the API-side write makes migration behave exactly like a normal onboard — the
destination binding only becomes durable once the onboarder proves it can read the league.

Requiring "proof of destination ownership" is not the fix: Sleeper has no auth and its
data/onboarding are already open, so ownership cannot be (and need not be) proven. Deferring the
write to the onboarder gives the correct per-platform result for free — ESPN destinations require
working cookies (closing the private-league squat); Sleeper destinations inherit the existing open
"first-to-onboard" model with no new exposure.

## What Changes

- **Remove the destination `LEAGUE_LOOKUP` `put_item` from `migrate_league`** in
  `src/api/routes.py`. The API continues to write the `PLATFORM_MIGRATION` mapping and update
  source `METADATA`, create the job, and invoke the onboarder, returning `202`.
- The destination `LEAGUE_LOOKUP` is now written **only** by the onboarder (`src/onboarder/writer.py`)
  after a successful destination fetch, so a failed/unauthorized migration leaves no mapping behind.
- **Harden the onboarder's MIGRATE `LEAGUE_LOOKUP` Put with a conditional expression**
  (`attribute_not_exists(PK)`) so a concurrent claim / check-then-write race cannot overwrite an
  existing destination mapping.

## Impact

- Specs: `backend/league-migration` (MODIFIED "Migrate a league to a new platform"; ADDED
  "Rollback-safe destination binding").
- Code: `src/api/routes.py` (drop the up-front destination `LEAGUE_LOOKUP` write);
  `src/onboarder/writer.py` (conditional Put on the MIGRATE destination lookup).
- Tests: backend component tests for the migrate flow (assert the API no longer writes the
  destination `LEAGUE_LOOKUP`, that it appears only after a successful onboarder run, and that a
  failed destination fetch leaves the destination ID onboardable); backend unit tests for the
  onboarder writer's conditional Put. No frontend or API-contract changes.
