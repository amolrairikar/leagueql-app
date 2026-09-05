## 1. Lambda source

- [x] 1.1 Create `src/admin_report/aggregations.py` with pure, pandas-free helpers over raw GSI3 items — `effective_platform`, a tolerant `_parse_ts`, `count_total`, `count_active(items, now, days=14)`, `platform_counts`, `new_onboards(items, now)` (24h/7d/30d). Verify via the aggregation unit tests in task 3.1.
- [x] 1.2 Create `src/admin_report/handler.py` with `lambda_handler(event, context)`: module-level `boto3.resource(...).Table(os.environ["DYNAMODB_TABLE_NAME"])`, a paginated GSI3 `Key("SK").eq("METADATA")` query, `now = datetime.now(timezone.utc)`, build a green Discord embed with the metric `fields`, and POST it via `common.http.build_retry_session()` + `common.secrets.get_secret_from_env_param("DISCORD_WEBHOOK_URL_SSM_PARAM")`, raising on unset webhook / non-2xx / query error. Verify via the handler unit tests in task 3.2.
- [x] 1.3 Create `src/admin_report/requirements.txt` containing `requests`. Verify it matches the deps actually imported (only `requests`; `boto3` is in the Lambda runtime).

## 2. Remove the Streamlit dashboard

- [x] 2.1 Delete `scripts/admin_dashboard/` (`dashboard.py`, `aggregations.py`, `README.md`) and `tests/unit/scripts/test_admin_dashboard_aggregations.py`. Verify `rg -l admin_dashboard` returns no source/test references.
- [x] 2.2 Remove `streamlit` and `plotly` from `Pipfile` `[dev-packages]` (keep `pandas` under `[packages]`). Verify `pipenv run pytest tests/unit/` still collects and passes.

## 3. Unit tests

- [x] 3.1 Add `tests/unit/admin_report/__init__.py` and `test_aggregations.py`, porting the dashboard aggregation cases and adding `new_onboards` cases (inside/outside each window, inclusive boundary, missing/unparseable `onboarded_at` excluded). Verify `pipenv run pytest tests/unit/admin_report/test_aggregations.py` passes.
- [x] 3.2 Add `tests/unit/admin_report/conftest.py` + `test_handler.py` (session-scoped autouse bootstrap patching env + `common.secrets.get_ssm_parameter` before import; mocked DDB table with paginating `query.side_effect`; patched session `.post`). Cover happy digest, pagination, empty table, unset-webhook RuntimeError, and post-failure re-raise. Verify `pipenv run pytest tests/unit/admin_report/ --cov=src/admin_report --cov-report=term-missing` is near-100%.

## 4. Component test (scoped)

- [x] 4.1 Add GSI3 (`SK` PK, `onboarded_at` SK) to `_create_table()` in `tests/component/environment.py` and load the new handler onto `context`, mocking the Discord `requests` POST. Verify `pipenv run behave tests/component` still passes on existing scenarios.
- [x] 4.2 Add a Behave scenario that seeds METADATA items, invokes the handler, and asserts the posted embed's counts. Verify `pipenv run behave tests/component` passes the new scenario. If adding GSI3 proves too broad, skip 4.1–4.2 and record the unit-only coverage decision here.

## 5. Infrastructure

- [x] 5.1 In `infrastructure/global/prod/main.tf`, add `module "admin-report-lambda-role"` (copy `sleeper-refresh-lambda-role`): logs on `/aws/lambda/leagueql-admin-report-${var.environment}-east(:*)`, `dynamodb:Query` on the primary table + `/index/GSI3`, and `ssm:GetParameter` on both regions' `.../discord/webhook_url`. Verify `terraform fmt -check` and `terraform validate` pass in `infrastructure/global/prod`.
- [x] 5.2 In `infrastructure/regional/main.tf`, add the `admin_report_role_arn` local, a `module "admin_report_lambda"` (`s3_key = "lambda-code-artifacts/admin_report-lambda.zip"`, env `DYNAMODB_TABLE_NAME`/`ENVIRONMENT`/`DISCORD_WEBHOOK_URL_SSM_PARAM`), and the `aws_cloudwatch_event_rule` (`cron(0 8 * * ? *)`) / `event_target` / `lambda_permission` trio, all gated `count = var.environment == "prod" && local.region == "east" ? 1 : 0`. Verify `terraform fmt -check` and `terraform validate` pass in `infrastructure/regional`.
- [x] 5.3 Append `./src/admin_report` to the `build_lambda_zip.sh` argument list in `.github/workflows/build.yaml`. Verify the dir name matches the Terraform `s3_key` basename (`admin_report`).

## 6. Docs

- [x] 6.1 Add the new scheduled Lambda (nightly EventBridge → admin-report Lambda → DynamoDB read + Discord) to `docs/architecture/architecture_diagram.py` and regenerate the PNG with `pipenv run python docs/architecture/architecture_diagram.py`. Verify the regenerated `leagueql_architecture.png` shows the new component.
- [x] 6.2 Update the GSI3 note in `docs/db/dynamodb_spec.md` to reference the nightly onboarding report. Verify wording no longer implies the metrics are dashboard-only.

## 7. Finalize

- [x] 7.1 Run `pipenv run ruff check --fix .` and `pipenv run ruff format .`; verify no lint errors remain.
- [x] 7.2 Run `openspec validate --all` and the full `pipenv run pytest tests/unit/`; verify both pass, then archive the change.
