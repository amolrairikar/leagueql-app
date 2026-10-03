# Tasks

## 1. Per-team guid resolution (shared helper + members proxy)

- [x] 1.1 In `src/common/yahoo_members.py`, add a masked-guid normalizer (`--hidden--`, `--`, empty → `None`) and change `resolve_team_owner_ids` to use each team's real guid when it is unique in the league, otherwise that team's `manager_id`. Verify with new cases in `tests/unit/common/test_yahoo_members.py`: all masked, mixed real/masked, a duplicated real guid falls back for those teams only, all real.
- [x] 1.2 Update `parse_managers` / members-proxy expectations for the per-team rule and verify `pipenv run behave tests/component/features/yahoo_members_proxy.feature` passes, adding a masked-guid scenario if the existing ones don't cover it.

## 2. Raw teams record keeps guid and slot id

- [x] 2.1 In `src/onboarder/yahoo_client.py` `_filter_teams`, add `guid` (real or null) and `slot_manager_id` to member and team rows, keeping `manager_id` = resolved owner id. Verify with `tests/unit/onboarder/test_yahoo_client.py` assertions for masked and real guids.
- [x] 2.2 Document the new raw team fields in the S3 raw-data section of `docs/db/dynamodb_spec.md` and verify the documented shape matches the unit-test fixture.

## 3. Cross-season identity resolution in the processor

- [x] 3.1 Add the pure `resolve_yahoo_owner_identities(teams_by_season)` to `src/processor/handler.py` (ordered passes guid → nickname → team name → custom logo; unambiguous, one-to-one per season; matching against all earlier seasons; `--hidden--`/duplicate-nickname and default-logo exclusions; legacy non-numeric `manager_id` treated as a guid; id = guid or first-season team key). Verify with unit tests in `tests/unit/processor/test_yahoo.py` covering every scenario of the "Resolve stable Yahoo owner identities across seasons" requirement, using only anonymized names ("Manager A", "Team X").
- [x] 3.2 Wire it into `_register_yahoo_raw_data` (new `identity_teams` argument, threaded through `register_raw_data` for YAHOO only) so `members.id`, `teams.primaryOwner`, and `teams.owners` use stable ids. Verify with a unit test that runs the TEAMS + MATCHUPS + STANDINGS transforms on a synthetic league with reassigned slots and asserts each champion appears under the correct distinct `owner_id`.
- [x] 3.3 Describe Yahoo `owner_id` semantics (real guid, or the first-season team key) in `docs/db/dynamodb_spec.md` and verify it agrees with the spec delta.

## 4. Consistency across incremental refreshes

- [x] 4.1 In `_process_manifest`, for YAHOO, read the `teams` records of manifest seasons outside `seasons_to_process` (parallel `read_s3_object`) and pass them as `identity_teams`. Verify with a processor unit test where only the latest season is processed and the resulting ids equal those from a full run.
- [x] 4.2 Add component scenarios to `tests/component/features/onboard_to_processed.feature` (+ steps): "A Yahoo league whose manager slots change across seasons keeps one owner per person", and a latest-season refresh that leaves owner ids unchanged. Use anonymized fixtures and verify with `pipenv run behave tests/component`.

## 5. Migration-mapping translation

- [x] 5.1 After identity resolution, translate an untranslated `PLATFORM_MIGRATION#*#YAHOO` item: map each `newPlatformOwnerId` through the latest season's raw owner id → stable id, leave `__not_returning__`/unmatched ids unchanged, and set `yahoo_owner_ids_resolved`. Verify with processor unit tests: translated once, then left alone on the next run (moto DynamoDB).
- [x] 5.2 Document the `yahoo_owner_ids_resolved` attribute under PLATFORM_MIGRATION in `docs/db/dynamodb_spec.md` and check `docs/api/openapi_spec.yaml` for any Yahoo-guid `owner_id` wording to update.

## 6. Integration checks and rollout

- [x] 6.1 Run `pipenv run ruff check --fix . && pipenv run ruff format .`, `pipenv run pytest tests/unit` (coverage near 100% on the changed modules), `pipenv run behave tests/component`, and `npx @fission-ai/openspec@latest validate --all`, and verify all of them pass.
- [x] 6.2 Grep the change directory, new tests, fixtures, and docs to confirm no real league, team, or manager names from `sample_data/` appear in any of them.
- [x] 6.3 Locally re-run the processor on `sample_data/` and confirm each season's champion maps to a distinct correct person and every person has one `owner_id` across their seasons. This check stays out of the repo.
- [x] 6.4 After deploy, run `scripts/utility_scripts/backfill_leagues.py --platform YAHOO` on dev, check Manager History for a Yahoo league, then run it on prod with `--execute`.
- [x] 6.5 Remove the temporary `fetch_yahoo_league_teams.py` and `yahoo_raw/` from the repo root.
