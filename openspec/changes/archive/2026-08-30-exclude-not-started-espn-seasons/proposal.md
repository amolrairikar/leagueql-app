## Why

A brand-new ESPN league that hasn't drafted yet returns `draftDetail = {"drafted": false, "inProgress": false}` with no `picks` key. This crashes onboarding: the onboarder's `_filter_draft_picks` does `data["draftDetail"]["picks"]` and raises `KeyError`, and if `picks` is instead an empty list the processor registers a 0-column `draft_picks` DuckDB view so the `DRAFT` (ESPN) transform fails to bind (`Binder Error: ... "ds" does not have a column named "memberId"`). Sleeper already handles the equivalent case (pre-draft/drafting seasons) by excluding not-yet-started seasons; ESPN has no equivalent rule.

## What Changes

- The onboarder excludes an ESPN season whose draft has not occurred (`draftDetail.drafted == false`) from the onboarded season list — it produces no S3 payload, no processed views, and no season-dropdown entry — mirroring the existing Sleeper `pre_draft`/`drafting` exclusion. Because ESPN's `status.previousSeasons` only ever lists completed (already-drafted) seasons, only `latest_season` can be pre-draft, which keeps detection to a single season.
- A brand-new ESPN onboard whose only season has not drafted fails with the existing `NOT_STARTED` job-status code and its platform-templated message, so the frontend surfaces the same "hasn't started a season yet" feedback it already shows for Sleeper. This reuses the platform-generic handler path that already gates on `client.get_seasons()` being empty.
- `_filter_draft_picks` no longer raises `KeyError` when `draftDetail` has no `picks` key (defensive; the excluded-season path means the processor should never see an empty ESPN `draft_picks` view in normal operation).

## Capabilities

### New Capabilities
<!-- none -->

### Modified Capabilities
- `backend/league-onboarding`: The "Exclude not-yet-started Sleeper seasons" requirement is generalized so the not-yet-started exclusion and the `NOT_STARTED` failure for a brand-new onboard whose only season hasn't started also cover ESPN (draft-not-occurred), in addition to the existing Sleeper `pre_draft`/`drafting` behavior.

## Impact

- **Code:** `src/onboarder/espn_client.py` (detect latest-season draft status, exclude it from `get_seasons()`; harden `_filter_draft_picks`), `src/onboarder/handler.py` (existing platform-generic `NOT_STARTED` path — verify it fires for ESPN).
- **Reuse:** `src/common/job_status.py` `NOT_STARTED` message is already `{platform}`-templated; no new UI code expected. Confirm the frontend onboarding error handling already surfaces `NOT_STARTED` for ESPN.
- **Tests:** onboarder unit tests (ESPN season exclusion, `NOT_STARTED` path, `_filter_draft_picks` with absent `picks`); backend component test for the ESPN `NOT_STARTED` onboarding outcome; a frontend scenario for the ESPN `NOT_STARTED` message if not already covered.
- **Specs:** `openspec/specs/backend/league-onboarding/spec.md`.
