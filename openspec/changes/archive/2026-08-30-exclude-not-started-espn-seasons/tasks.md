## 1. ESPN onboarder — exclude not-yet-drafted latest season

- [x] 1.1 In `src/onboarder/espn_client.py` `_get_league_seasons`, add `mDraftDetail` to the latest-season status request (`view=mTeam&view=mDraftDetail`) and drop `latest_season` from the returned list when `draftDetail.drafted` is `false`; verify a new unit test asserts the returned seasons exclude an undrafted latest season while keeping completed prior seasons.
- [x] 1.2 Route the refresh path (`is_refresh=True`) through the same latest-season draft-status check so an undrafted current season yields an empty `get_seasons()`; verify a unit test shows a refresh of a pre-draft latest season returns no seasons.
- [x] 1.3 Harden `_filter_draft_picks` to tolerate an absent `picks` key (return an empty `draft_picks` list); verify a unit test passes `draftDetail = {"drafted": false, "inProgress": false}` and gets `{"draft_picks": []}` with no `KeyError`.

## 2. Not-started outcome wiring

- [x] 2.1 Confirm the handler `NOT_STARTED` path (`src/onboarder/handler.py` ~274) fires for an ESPN `ONBOARD` whose only season is undrafted (empty `get_seasons()`), and that a REFRESH of an undrafted-only ESPN league lands on the no-op `COMPLETED` success; verify via unit test(s) over the handler for both request types.
- [x] 2.2 Verify `src/common/job_status.py` `NOT_STARTED` message templates correctly for ESPN (`{platform}` → ESPN); add/adjust a unit test asserting the rendered message.

## 3. Component & frontend coverage

- [x] 3.1 Add a backend component test (`tests/component`) for an ESPN `ONBOARD` of a brand-new undrafted league asserting the `NOT_STARTED` failure outcome (400, failure job status, no S3/views written).
- [x] 3.2 Confirm the frontend onboarding flow already surfaces the `NOT_STARTED` message for ESPN; if a scenario is missing, add/extend the jest-cucumber pair under the onboarding feature so the ESPN `NOT_STARTED` case is covered. Verify with `npx vitest run <path>`.

## 4. Validation

- [x] 4.1 Run `pipenv run ruff check --fix . && pipenv run ruff format .`, the affected backend unit tests (`pipenv run pytest tests/unit/onboarder`), the ESPN onboarding component test (`pipenv run behave tests/component`), and `openspec validate exclude-not-started-espn-seasons --strict`; verify all pass.
