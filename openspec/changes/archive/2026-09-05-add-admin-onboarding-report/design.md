## Context

See `proposal.md` — Why. The metrics already exist in the Streamlit dashboard
(`scripts/admin_dashboard/`), driven by a single GSI3 `SK = "METADATA"` query and pure pandas
aggregation helpers. The codebase already has the two patterns this change composes:

- **Scheduled Lambdas** (`sleeper_refresh`, `player_metadata`): a `modules/lambda` block plus an
  `aws_cloudwatch_event_rule` / `event_target` / `lambda_permission` trio in
  `infrastructure/regional/main.tf`, gated `count = local.region == "east" ? 1 : 0` (scheduled jobs
  run in one region), with an IAM role in `infrastructure/global/<env>/main.tf`.
- **Discord posting** (`src/discord_notifier/handler.py`): fetch the webhook URL from a SecureString
  SSM parameter at cold start via `common.secrets.get_secret_from_env_param`, build an embed, and
  `POST {"embeds": [embed]}` with `raise_for_status()`.

Lambda deployment packages are pip-installed per-dir `requirements.txt` + vendored `src/common/`,
zipped by `scripts/deployment_scripts/build_lambda_zip.sh` from an explicit dir list in
`.github/workflows/build.yaml`, and pulled from S3 by the Terraform `modules/lambda`.

## Goals / Non-Goals

**Goals:**
- A self-contained nightly Lambda that reuses the existing scheduled-Lambda and Discord-post
  patterns with no new architectural concepts.
- Keep the deployment package small and cold-start-light.
- Preserve the dashboard's metric semantics (effective platform, inclusive 14-day active window,
  missing/unparseable timestamps excluded) so the numbers stay comparable.

**Non-Goals:**
- Rendering the cumulative-onboarding chart as an image (replaced by 24h/7d/30d deltas).
- Deploying to dev, or to us-west-2 (prod-only, east-only).
- Any new alerting topic — failures surface through the Lambda's own CloudWatch error metric.

## Decisions

- **Port the aggregations into `src/` without pandas.** pandas is a production dependency and could
  be imported, but the helpers only do counts and window comparisons; plain `datetime`/dict math
  keeps the zip small and avoids coupling `src/` to `scripts/`. Alternative (import the existing
  `scripts/admin_dashboard/aggregations.py`) was rejected — `scripts/` is not part of a Lambda
  deploy artifact, and pandas is heavy for a tiny job.
- **Reuse the existing Discord webhook and SSM parameter** (`/leagueql/<env>/discord/webhook_url`)
  rather than a new channel/parameter. The nightly digest is informational (green embed), visually
  distinct from the red alert embeds, so a shared channel is acceptable and avoids new secrets.
- **Copy, don't share, the ~4-line embed-POST.** There is no `common/` Discord poster; the
  `discord_notifier` handler is bound to the SNS envelope. Replicating the small POST against
  `common.http.build_retry_session()` keeps each Lambda independent (the repo's norm), accepting
  that the shared session does not retry POSTs — same as the existing notifier.
- **Gate prod-and-east.** Existing scheduled Lambdas gate east-only but deploy to both envs; this
  one additionally restricts to prod (`count = var.environment == "prod" && local.region == "east"
  ? 1 : 0`) because the data source and Discord channel are prod-only. The IAM role therefore lives
  only in `infrastructure/global/prod/main.tf`.
- **Delete the Streamlit dashboard** rather than keep both. It becomes redundant, and dropping
  `streamlit`/`plotly` from dev deps trims the toolchain. `pandas` stays (used elsewhere in
  `[packages]`).

## Risks / Trade-offs

- **GSI3 absent from the component-test harness** → the moto table in
  `tests/component/environment.py` defines only GSI1/GSI2. Add GSI3 to `_create_table()` for a
  component scenario; if that proves too broad, rely on unit tests (mocked DDB client, per the
  `sleeper_refresh` pattern) and note the gap in `tasks.md`.
- **POST is not retried** by the shared retry session → a transient Discord 5xx fails the run.
  Acceptable: EventBridge and the nightly cadence tolerate an occasional miss, and the failure is
  visible in the Lambda's error metric — matching the existing notifier's behavior.
- **Shared alert channel noise** → a nightly informational message lands alongside red alerts.
  Mitigated by the distinct green embed and low (once-daily) frequency.

## Migration Plan

- Deploy is additive: new Lambda + schedule + role, plus adding `./src/admin_report` to the
  build-zip list. The Streamlit removal is dev-tooling only (no runtime impact).
- Rollback: disable/remove the `aws_cloudwatch_event_rule` (or the whole prod-east module) to stop
  the nightly run; the removed dashboard can be restored from git history if ever needed.
