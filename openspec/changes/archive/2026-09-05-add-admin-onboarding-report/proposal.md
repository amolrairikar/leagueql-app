## Why

Onboarding-health metrics (total leagues, active leagues, platform split, onboarding trend)
are only visible today through a read-only Streamlit dashboard (`scripts/admin_dashboard/`) that
a developer has to run by hand against prod. Nobody sees the numbers unless they remember to
launch the app, so onboarding trends go unnoticed. Replacing the pull-based dashboard with a
push-based nightly digest to the existing Discord channel surfaces the same health signal
automatically, with no one having to run anything.

## What Changes

- Add a new **scheduled Lambda** (`src/admin_report/`) that runs nightly at **08:00 UTC**
  (EventBridge cron), queries the GSI3 "all-leagues" index (`SK = "METADATA"`, paginated), and
  posts a single formatted digest to the existing LeagueQL Discord webhook.
- The digest reports: total leagues onboarded, active leagues (accessed in the last 14 days), the
  ESPN-vs-SLEEPER split (using `active_platform` when a league has migrated), and new-onboards
  counts for the last 24h / 7d / 30d (replacing the dashboard's cumulative time-series chart,
  which does not translate to a text message).
- On a DynamoDB-query or Discord-post failure the Lambda raises so the error surfaces in its own
  CloudWatch error metrics; it does **not** re-publish to the alert SNS topic (same rationale as
  the existing `discord_notifier`).
- Deploys **prod-only, east-only** (matches the prod-only data source and the existing
  `discord_notifier`); reuses the same `/leagueql/<env>/discord/webhook_url` SecureString SSM
  parameter.
- **BREAKING (dev tooling only):** the Streamlit dashboard at `scripts/admin_dashboard/`
  (`dashboard.py`, `aggregations.py`, `README.md`) and its unit test are removed. No
  externally-observable product behavior is affected by the removal.

## Capabilities

### New Capabilities
- `backend/admin-onboarding-report`: A scheduled backend job that periodically aggregates
  onboarding-health metrics from the DynamoDB METADATA items and pushes a digest to an admin
  Discord channel.

### Modified Capabilities
<!-- None. The removed Streamlit dashboard was an ad-hoc script with no capability spec. -->

## Impact

- **New code:** `src/admin_report/{handler.py,aggregations.py,requirements.txt}` and its unit
  tests under `tests/unit/admin_report/`.
- **Infrastructure:** a new Lambda + IAM role (`infrastructure/global/prod/main.tf`) and the
  EventBridge schedule/target/permission wiring (`infrastructure/regional/main.tf`); the new
  source dir added to the Lambda-zip build list in `.github/workflows/build.yaml`.
- **Removals:** `scripts/admin_dashboard/` and `tests/unit/scripts/test_admin_dashboard_aggregations.py`;
  the now-unused `streamlit` and `plotly` dev dependencies dropped from `Pipfile` (`pandas` stays —
  it is a production dependency used elsewhere).
- **Docs:** the architecture diagram (`docs/architecture/architecture_diagram.py` + regenerated
  PNG) gains the new scheduled component; the GSI3 note in `docs/db/dynamodb_spec.md` references
  the nightly report.
- **Data source:** read-only `dynamodb:Query` on the primary table's GSI3; no writes. Reuses the
  existing Discord webhook SSM parameter and alert channel.
