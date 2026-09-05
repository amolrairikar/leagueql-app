# Component Tests (backend)

Component tests exercise whole components — the onboarder→processor chain, the
FastAPI app, the Sleeper auto-refresh Lambda — with every **external** dependency
mocked. They sit between `tests/unit/` (fine-grained, near-100% coverage) and
`tests/integration/` (behave against the **real** dev AWS stack).

## Running

```bash
pipenv run behave tests/component
```

No AWS credentials are needed — AWS is backed by `moto` (`mock_aws`).

## How the harness works (`environment.py`)

- `before_all` starts `mock_aws()`, creates the DynamoDB table (PK/SK + **GSI1**
  on `canonical_league_id`, **GSI2** on `platform`/`league_id`, and **GSI3** on
  `SK`/`onboarded_at`, matching `infrastructure/modules/dynamodb/main.tf`) and a
  **versioned** S3 bucket, seeds the Discord-webhook SSM parameter, then loads
  every Lambda handler + the API.
- Modules are imported **after** moto starts, so every module-level `boto3`
  client is moto-backed with no per-module patching.
- Lambda handlers share bare module names (`utils`, `queries`, `handler`); each
  component is loaded with its bare-name imports resolved, then its handler
  reference is stashed on `context` (`context.onboarder_handler`,
  `context.processor_handler`, `context.refresh_handler`,
  `context.api` = FastAPI `TestClient`). Steps always reach handlers through
  `context`, never the last-writer-wins bare names.
- `context.main.lambda_client` is a `MagicMock` (moto[s3,dynamodb] has no Lambda),
  so the API's async onboarder invoke is asserted, not executed.
- `before_scenario` resets the Lambda spy and a `context._patches` list; steps
  append started `unittest.mock.patch` handles to it and `after_scenario` stops
  them, then clears the table and bucket for isolation.

## Mocking the platform boundary

- The onboarder→processor chain mocks the platform API by replacing
  `OnboardingService._build_client` with a fake client that returns fixture raw
  data (`tests/component/fixtures/`); the real writer→S3, DynamoDB, processor and
  DuckDB transforms all run.

## Conventions

- Feature files live in `features/`, step defs in `steps/` (shared seeding +
  assertions in `common_steps.py`). Fixtures in `fixtures/`.
- All step code must pass `pipenv run ruff check` and `ruff format`.
- Keep fixtures small (≈2 owners, 2 weeks) so DuckDB runs fast and assertions
  stay legible. Every DuckDB-referenced table needs ≥1 well-formed row — an empty
  pandas frame has no columns and breaks DuckDB binding.
