## 1. API — drop the up-front destination lookup write

- [x] 1.1 In `src/api/routes.py` `migrate_league`, remove the `main.table.put_item(...)` that writes
      the destination `LEAGUE#{newPlatformLeagueId}#PLATFORM#{newPlatform}` / `LEAGUE_LOOKUP` item.
      Keep the `PLATFORM_MIGRATION` put, the `METADATA` update, the job creation, and the onboarder
      invoke unchanged. Confirm the `202` response shape is unchanged.

## 2. Onboarder — conditional destination lookup write

- [x] 2.1 In `src/onboarder/writer.py`, add `ConditionExpression: attribute_not_exists(PK)` to the
      MIGRATE `LEAGUE_LOOKUP` `Put` so it cannot overwrite an existing destination mapping.
- [x] 2.2 Handle the conditional-check failure as a recorded FAILED job ("destination already
      onboarded"), not an unhandled exception. (Cancelled MIGRATE transaction is logged distinctly
      and re-raised; the handler's existing FAILED-recording path catches it.)

## 3. Tests

- [x] 3.1 Backend component (`tests/component`): the migrate scenario now asserts the API returns
      `202` and writes `PLATFORM_MIGRATION` but **not** the destination `LEAGUE_LOOKUP` (the mocked
      onboarder Lambda would write it after a successful fetch).
- [x] 3.2 Backend component: added a scenario in `onboard_to_processed.feature` — the onboarder fails
      a MIGRATE destination fetch (401), asserting `502`, a FAILED `JOB_STATUS`, and no destination
      `LEAGUE_LOOKUP` written. Driven by the `the onboarder fails a MIGRATE destination fetch ...`
      step in `onboarding_steps.py`.
- [x] 3.3 Backend unit (`tests/unit`): cover the onboarder writer's conditional Put — the MIGRATE Put
      carries `attribute_not_exists(PK)`, and a `TransactionCanceledException` re-raises
      (`test_migrate_conditional_failure_propagates`). Added an API-level test that the migrate
      endpoint writes no `LEAGUE_LOOKUP` (`test_does_not_write_destination_lookup`).

## 4. Quality gates

- [x] 4.1 `pipenv run ruff check --fix .` and `pipenv run ruff format .`.
- [x] 4.2 `pipenv run behave tests/component` (60 scenarios) and `pipenv run pytest tests/unit` (772)
      pass.
- [x] 4.3 `openspec validate --all` passes.
