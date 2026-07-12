# BE-002: League Refresh

## Description
Refreshes data for an already-onboarded league to pull in newly completed weeks/seasons.
Triggered by `POST /leagues?requestType=REFRESH`. Reuses the same onboarder + processing
pipeline as onboarding ([BE-001](BE-001-league-onboarding.md), [BE-004](BE-004-data-processing-pipeline.md))
but writes against the existing canonical league ID and S3 prefix, overwriting precomputed
views in place. The endpoint enforces a per-league refresh cooldown and short-circuits
when the league is already up to date based on current NFL state.

## Scope
- Endpoint: `POST /leagues?requestType=REFRESH` (`src/api/routes.py::onboard_league`).
- Cooldown constant: `REFRESH_COOLDOWN_MINUTES` (`src/api/main.py`).
- NFL state + latest-matchup checks: `get_nfl_state`, `get_latest_stored_matchup`.
- **Recap generation:** a refresh runs through the processor, which fires the recap-generator
  Lambda at end of run ([BE-004](BE-004-data-processing-pipeline.md) /
  [BE-021](BE-021-ai-weekly-matchup-recap.md)) so a premium league's newly-completed week gets an
  AI recap; idempotent + premium-gated, so it is a no-op otherwise.

## Edge Cases
- **Refresh already in progress:** if `METADATA` shows an active job, return `409`.
- **Cooldown active:** if `last_refresh_at` is within `REFRESH_COOLDOWN_MINUTES`, return
  `429` with a wait message.
- **NFL offseason:** if NFL state `season_type == "off"`, return `409`
  "League is already up to date (NFL offseason)."
- **Already current:** if the latest stored matchup `(season, week)` is `>=` the current
  NFL state, return `409` "League is already up to date."
- **ESPN refresh season:** must use the user-entered `latestSeason` from the request, not
  the previously-onboarded season returned by `getLeague`. (See memory: ESPN refresh season bug.)
- **AI recaps are not idempotent:** any AI-generated season recaps must be overwritten on
  refresh, not skipped. (See memory: AI recap idempotency.)
- **Sleeper league not yet in `LEAGUE_LOOKUP`:** allowed — the onboarder resolves the
  canonical league via the `previous_league_id` chain (does not 404 like ESPN would).
- **New Sleeper season not yet started:** when a refresh/onboard resolves an existing league
  but only a not-yet-started season (latest league `status` is `pre_draft`/`drafting`, e.g. an
  offseason renewal), the onboarder finds no usable seasons and treats it as a **no-op
  success** — it does not fetch data and marks the `JOB_STATUS` `COMPLETED` so the frontend
  stops polling. It **does** register the new league ID as a **pending** `LEAGUE_LOOKUP`
  (mapped to the existing canonical, marked `pending_season`, with no `seasons` yet) so the
  scheduled auto-refresh ([BE-012](BE-012-scheduled-sleeper-auto-refresh.md)) can poll it and
  promote it to a real season once it flips to `in_season`. (Sleeper only links seasons
  backwards, so without this record the new season could never be auto-discovered — see
  [BE-001](BE-001-league-onboarding.md).) A poll of an **already-pending** league ID (the
  canonical is passed in, so the chain walk is skipped) that is still not started leaves the
  pending record untouched.
- **Refresh of a non-existent ESPN league:** returns `404`.
- **NFL state fetch fails:** refresh should still be allowed to proceed (degrade safely).

## Acceptance Criteria
- [ ] `POST /leagues?requestType=REFRESH` on an existing league returns `201` with a
      `correlation_id` and invokes the onboarder against the existing canonical league ID.
- [ ] A second refresh while one is in progress returns `409`.
- [ ] A refresh within the cooldown window returns `429` with the remaining wait time.
- [ ] A refresh during the NFL offseason or when data is already current returns `409`.
- [ ] Precomputed views are overwritten in place (same canonical league ID / S3 prefix);
      `LEAGUE_COUNT` is not incremented.
- [ ] ESPN refreshes use the user-entered latest season.
- [ ] On success `last_refresh_at` is updated to enforce the next cooldown window.
- [ ] A refresh/onboard that resolves an existing league but only a not-yet-started Sleeper
      season (`pre_draft`/`drafting`) is a no-op success (`JOB_STATUS` `COMPLETED`, no fetch)
      that registers a **pending** `LEAGUE_LOOKUP` (new league ID → existing canonical,
      `pending_season` marker, no `seasons`); a later poll of an already-pending ID leaves it
      untouched until the season starts.

## Authorization (BE-016)
Refresh is **owner-gated** ([BE-016](BE-016-league-ownership-authorization.md)): a non-owner caller gets `403`.

## Sources
`src/api/routes.py`, `src/api/main.py`, `src/onboarder/`, memory: `feedback_espn_refresh_season`,
`feedback_ai_recap_idempotency`.
