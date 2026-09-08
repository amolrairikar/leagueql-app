## Context

The migration endpoint (`src/api/routes.py:migrate_league`) performs three synchronous DynamoDB
writes before firing the async onboarder:

1. `LEAGUE_LOOKUP` for `LEAGUE#{newPlatformLeagueId}#PLATFORM#{newPlatform}` → canonical
2. `PLATFORM_MIGRATION#{from}#{to}` manager mapping
3. `METADATA` update (`active_platform`, `migrated_from`, `migrated_at`, `active_job_id`, `platform`)

Write (1) is the security problem (SEC-01): it is created before any validation that the caller can
read the destination league, and it is never rolled back if the onboarder fails.

## Key finding: the API-side write is redundant

`src/onboarder/writer.py` already writes the destination `LEAGUE_LOOKUP` on the MIGRATE path
(lines ~194–211), and that write only runs at the tail of a **successful** `OnboardingService.run()`
— i.e. after the onboarder has fetched the destination-platform league. So the correct destination
binding already exists in the success path; the API's up-front write merely duplicates it and, as a
side effect, persists a squat on failure.

## Decision

- **Remove the API-side destination `LEAGUE_LOOKUP` write entirely.** Keep writes (2) and (3): the
  `PLATFORM_MIGRATION` mapping and `METADATA` update are on the caller's *own* canonical league (which
  they own), and the onboarder needs the mapping to resolve cross-platform owner IDs. They carry no
  squatting power because they do not create a resolvable destination lookup.
- **Make the onboarder's MIGRATE `LEAGUE_LOOKUP` Put conditional** on `attribute_not_exists(PK)` so a
  race between the endpoint's "already onboarded?" check and the onboarder's write cannot silently
  overwrite a destination mapping that appeared in between. A conditional-check failure is treated as
  "destination already claimed" and recorded as a failed job, not a crash.

## Per-platform outcome (why no ownership proof is needed)

- **ESPN destination:** the onboarder cannot fetch a private ESPN league without valid `s2`/`swid`,
  so a caller who does not control the destination gets a failed fetch and **no** `LEAGUE_LOOKUP` is
  written — the real owner keeps the ability to onboard it. This closes the squat.
- **Sleeper destination:** Sleeper data and onboarding are already open (documented, accepted), and
  there is no Sleeper auth to prove ownership. Deferring the write simply makes migrate match the
  normal Sleeper onboard's "first-to-onboard" behavior — no new capability is granted.

## Alternatives considered

- *Verify destination ownership in the API before writing:* rejected — impossible for Sleeper (no
  auth), and for ESPN it duplicates exactly the fetch the onboarder already performs.
- *Write the lookup up front but roll it back on onboarder failure:* rejected — brittle (the failure
  path is async and best-effort) and still leaves a squat window; removing the redundant write is
  simpler and strictly safer.

## Risks

- Low. The destination lookup is written a few seconds later (when the onboarder finishes) instead of
  immediately. Migration is already an async `202`-then-poll flow, and the frontend polls the job
  status rather than the destination lookup, so no client-visible contract changes.
