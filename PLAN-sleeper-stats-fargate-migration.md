# Convert Sleeper Player Stats Refresher: Lambda → ECS Fargate (cron)

## Context

The `sleeper_player_stats_refresher` Lambda fans out one HTTP request per active NFL
player to the Sleeper API, rate-limited to ~925 req/min. A full roster (thousands of
players) regularly approaches — and sometimes crosses — Lambda's hard **15-minute (900s)
timeout**, causing failed runs. The fix is to run the same logic as an **ECS Fargate
task**, which has no 15-minute cap, on a **weekly cron** instead of the current S3-event
trigger.

Two repos are involved:

- **`aws-account-management`** — owns account/network-level infra. We add a small, secure
  shared VPC (public subnet + locked-down security group) that lets the Fargate task reach
  the internet, plus the CI-role IAM permission additions needed for leagueql-app to manage
  ECS/ECR. Applied **manually by the user** with their own creds (this repo has no CI).
- **`leagueql-app`** — owns the application. We convert the handler, add a Dockerfile + ECR
  repo + ECS cluster/task-definition + a CloudWatch Events schedule rule, and remove the
  Lambda.

### Decisions locked with the user
- **Schedule:** weekly `cron(15 12 ? * TUE *)` (UTC) — 15 min after the Tuesday
  player-metadata refresh (`cron(0 12 ? * TUE,THU *)`), so metadata is fresh. This
  **replaces** the current S3-event trigger (the Thursday refresh no longer drives stats).
- **Egress:** task runs in a **public subnet with a public IP**; security group allows
  **no inbound**, all outbound. Near-zero idle cost (no NAT gateway). S3 reached via a
  **free VPC gateway endpoint**.
- **Cross-repo wiring:** leagueql-app discovers the VPC/subnets/SG via **tag-filtered
  `data` sources** — no Terraform state coupling (matches the repos' current independence).

---

## Part A — `aws-account-management`: secure shared VPC + CI permissions

> Applied by the user locally **before** leagueql-app CI runs (the data sources below
> require the VPC to already exist).

### A1. New module `infrastructure/modules/networking/` (matches repo's module pattern)
The repo already factors shared infra into modules (`./modules/api_gateway_dashboard`,
called from `infrastructure/main.tf`). Add a `networking` module the same way rather than an
inline file: `modules/networking/{main.tf,variables.tf,outputs.tf}`, instantiated from
`infrastructure/main.tf` as `module "fargate_networking" { source = "./modules/networking" }`.

One shared VPC (`environment = "all"`) used by both dev and prod tasks:
- `aws_vpc.fargate` — CIDR `10.0.0.0/16`, DNS support + hostnames enabled.
- `aws_internet_gateway.fargate`.
- 2× `aws_subnet.public` across `us-east-1a` / `us-east-1b` (`10.0.1.0/24`, `10.0.2.0/24`).
- `aws_route_table` with default route `0.0.0.0/0 → IGW` + associations.
- `aws_security_group.fargate_task` — **ingress: none**, **egress: 443 (and 80) to
  `0.0.0.0/0`**. This is the "secure" part: outbound-only.
- `aws_vpc_endpoint.s3` — gateway endpoint associated with the route table (free; keeps
  S3 traffic in-AWS, off the IGW).
- **Tagging — project convention (4 keys on _every_ resource).** Each VPC/subnet/IGW/route-
  table/SG/endpoint carries the standard set
  `project=leagueql / component=networking / environment=all / managed-by=terraform`
  (matching the tag blocks already used throughout `aws-account-management/infrastructure/main.tf`).
- **Discovery tags (on top of the 4 standard tags).** Because all networking resources share
  `component=networking, environment=all`, those 4 keys can't disambiguate the VPC from a
  subnet for leagueql-app's `data` lookups. Add a discriminating `Name` on the VPC
  (`leagueql-fargate-vpc`) and SG (`leagueql-fargate-task-sg`), and `tier = "public"` on the
  subnets, used as the filter values in Part B's data sources.
- **Outputs:** `vpc_id`, `public_subnet_ids`, `task_security_group_id` (for visibility /
  potential future state-based wiring; leagueql-app still discovers via tags, not these).

### A2. CI-role permission additions
Edit **both** `iam/github-actions-dev-role/terraform-dev-role-iam.json` and
`iam/github-actions-prod-role/terraform-prod-role-iam.json` to let leagueql-app CI manage
the new resources:
- `ecr:*` on `leagueql*` repos (create repo, push/pull images).
- `ecs:*` on `leagueql*` clusters/task-defs (create cluster, register task def, run task).
- **No `scheduler:*` needed** — the schedule is a CloudWatch Events rule (see B4), the same
  `aws_cloudwatch_event_rule` resource type the repo already manages for
  `player-metadata-refresh` and `sleeper-refresh`, so the existing `events:*` CI permission
  already covers it.
- `ec2:Describe*` (read-only — required for the VPC/subnet/SG data-source lookups).
- New `logs:*` resource ARN: `/ecs/leagueql*{env}*`.
- Extend the existing **`IAMPassRole`** condition's `iam:PassedToService` list with
  `ecs-tasks.amazonaws.com` and `events.amazonaws.com` (the existing block already allows
  passing to s3/lambda/apigateway; `events.amazonaws.com` is the rule's `RunTask` invoke
  role, replacing the dropped `scheduler.amazonaws.com`).

The `iam:*` on `role/leagueql*{env}*` already covers creating the task roles (named
`leagueql-{env}-...`), so no change there.

---

## Part B — `leagueql-app`: handler, packaging, infra, scheduling

### B1. Convert the handler to a standalone script
`src/sleeper_player_stats_refresher/handler.py`
- Replace `def lambda_handler(event, context)` with `def main()` that reads the (test-only)
  overrides from **env vars** instead of an event dict:
  `SEASON` → `season_override`, `MAX_PLAYERS` → `max_players`, `OUTPUT_KEY` → `output_key`.
  The scheduled run sets none, preserving full production behavior (off-season skip, full
  fan-out, canonical output key).
- Keep `fetch_nfl_state`, `fetch_stats`, the rate limiter, and the S3 deep-merge logic
  unchanged. Off-season skip becomes a clean `return` / `sys.exit(0)`.
- Add `if __name__ == "__main__": main()`.
- `utils.py` (re-exports `build_retry_session`, `logger` from `src/common/`) is unchanged
  and gets vendored into the image.

### B2. New `src/sleeper_player_stats_refresher/Dockerfile`
- Base `python:3.13-slim`; `WORKDIR /app`.
- Build context = `./src`; copy `sleeper_player_stats_refresher/handler.py` + `utils.py`
  to `/app` and `common/` to `/app/common` (so both `from utils import …` and
  `from common.http import …` resolve, exactly as the zip vendors them).
- `pip install -r requirements.txt` (just `requests` + `boto3` — add `boto3` to
  `requirements.txt`; the Lambda got it from the runtime).
- `CMD ["python", "handler.py"]`.

### B3. ECR repo + IAM roles — `infrastructure/global/{dev,prod}/main.tf`
- `aws_ecr_repository.sleeper_player_stats_refresher` — `leagueql-sleeper-player-stats-refresher-{env}`,
  scan-on-push, a lifecycle policy keeping the last ~10 images.
- **Repurpose** the existing `sleeper-player-stats-refresher-lambda-role` module block
  (lines ~715-785) into the **ECS task role**: change the trust principal from
  `lambda.amazonaws.com` → `ecs-tasks.amazonaws.com`, drop the `logs:CreateLogGroup`/stream
  statements (the exec role + Terraform-created log group handle logging), keep the
  **S3 `ReadPlayerMetadata` + `WritePlayerStats`** statements as-is. Rename to
  `leagueql-{env}-sleeper-player-stats-refresher-task-role`.
- New **task execution role** `leagueql-{env}-sleeper-stats-task-exec-role` — trust
  `ecs-tasks.amazonaws.com`; permissions: ECR pull (`ecr:GetAuthorizationToken`,
  `BatchGetImage`, `GetDownloadUrlForLayer`) + `logs:CreateLogStream`/`PutLogEvents` on the
  task log group.
- New **events invoke role** `leagueql-{env}-sleeper-stats-events-role` — trust
  `events.amazonaws.com` (CloudWatch Events rule, not EventBridge Scheduler); permissions:
  `ecs:RunTask` on the task def + `iam:PassRole` for the task role and exec role.
- Reuse the existing `../../modules/iam-role` module for all three (same pattern as the
  current refresher role).

### B4. ECS cluster, task definition, schedule — `infrastructure/regional/main.tf` (east only)
Replace the `module "sleeper_player_stats_refresher_lambda"` block (lines 329-356) with,
guarded by `count = local.region == "east" ? 1 : 0`:
- `aws_ecs_cluster.leagueql` — `leagueql-{env}` (Fargate; can enable Container Insights).
- `aws_cloudwatch_log_group` — `/ecs/leagueql-sleeper-player-stats-refresher-{env}`,
  7-day retention.
- **Data sources** (tag lookups from Part A): `data.aws_vpc.fargate`,
  `data.aws_subnets.public`, `data.aws_security_group.fargate_task`.
- `aws_ecs_task_definition.sleeper_player_stats_refresher` — Fargate, `cpu = 512`,
  `memory = 1024`, `awslogs` driver → the log group, container image
  `"${ecr_repo_url}:${var.image_tag}"`, env `S3_BUCKET_NAME` (same bucket name as today),
  `execution_role_arn` + `task_role_arn` from B3. Add a new `image_tag` variable to
  `infrastructure/regional/variables.tf` (default `latest`), passed from CI as the git SHA.
- **Schedule via CloudWatch Events rule** (matches the existing `player_metadata_schedule` /
  `sleeper_refresh_schedule` pattern at `regional/main.tf:212,268` — not EventBridge
  Scheduler):
  - `aws_cloudwatch_event_rule.sleeper_player_stats_refresher` —
    `schedule_expression = "cron(15 12 ? * TUE *)"` (CloudWatch cron is UTC).
  - `aws_cloudwatch_event_target` with an `ecs_target` block: `task_definition_arn`,
    `launch_type = "FARGATE"`, `task_count = 1`, `network_configuration` using the discovered
    public subnets, the task SG, and `assign_public_ip = true`; target-level `role_arn` =
    the events invoke role from B3.

### B5. Remove Lambda wiring + monitoring
- `infrastructure/global/{dev,prod}/main.tf` — delete the `primary_event_notifications`
  entry (lines ~132-145) that triggers the refresher on `player-metadata/` puts (the cron
  replaces it). The auto-generated `aws_lambda_permission` in `modules/s3` drops with it.
- `infrastructure/regional/main.tf` — remove the Lambda's CloudWatch error alarm
  (`player_stats_refresher_errors`, lines ~552-577; metric-based alarms don't fit a one-shot
  Fargate task — there's no per-run `Errors` metric). **Replace** with prod monitoring keyed
  on **ECS Task State Change** events (same `count = local.region == "east" && prod` gate):
  - `aws_cloudwatch_event_rule.sleeper_stats_task_failed` — `event_pattern` on
    `source = ["aws.ecs"]`, `detail-type = ["ECS Task State Change"]`, scoped to **this**
    cluster + task-def (`detail.clusterArn` / `detail.taskDefinitionArn`), matching
    `detail.lastStatus = ["STOPPED"]` and a failure — i.e. **either** a non-zero container
    exit (`detail.containers.exitCode` = `[{ "anything-but": 0 }]`) **or** a start failure
    (`detail.stopCode = ["TaskFailedToStart"]`, where no `exitCode` is emitted). Covering
    both avoids missing image-pull/networking failures that never run the container.
  - `aws_cloudwatch_event_target` → existing `aws_sns_topic.lambda_alerts[0]` so failures
    still email `arairikar1@gmail.com`. **New requirement:** the topic has no
    `aws_sns_topic_policy` today — CloudWatch alarms publish within-account by default, but
    EventBridge does **not**. Add an `aws_sns_topic_policy` granting `events.amazonaws.com`
    `SNS:Publish` on `lambda_alerts` (scoped with `aws:SourceArn` = the event rule ARN),
    otherwise the notification silently fails to deliver.
- `local.sleeper_player_stats_refresher_role_arn` references — update to the new task-role
  ARN (or remove if unused after the rename).

### B6. Build pipeline — `.github/workflows/build.yaml`
- Remove `./src/sleeper_player_stats_refresher` from the `build_lambda_zip.sh` arg list
  (line 201) — it's no longer a zip artifact.
- Add a **`deploy-fargate-image`** job after `deploy-global` (so the ECR repo exists):
  configure AWS via the existing OIDC script, `aws ecr get-login-password | docker login`,
  `docker build` (context `./src`, the new Dockerfile), tag with the **git short SHA** +
  `latest`, push both. Make `deploy-regional` `needs:` this job and pass
  `-var="image_tag=<sha>"` into the regional `terraform apply`.

### B7. Tests + docs
- `tests/unit/sleeper_player_stats_refresher/test_handler.py` — switch from invoking
  `lambda_handler({...}, None)` to calling `main()` with the overrides set via
  monkeypatched env vars (`SEASON`/`MAX_PLAYERS`/`OUTPUT_KEY`). Keep coverage ~100%
  including the off-season skip, no-cache bootstrap, and deep-merge paths.
- **Integration tests — yes.** `tests/integration/player_stats/steps/player_stats_steps.py`
  invokes via `lambda_client.invoke` (`step_invoke_deployed`, ~line 67-82) with a JSON
  `invoke_payload`. Rewrite to `ecs:RunTask` (`launchType=FARGATE`, the discovered
  network config) with `MAX_PLAYERS`/`OUTPUT_KEY`/`SEASON` passed as **container env
  overrides** (`overrides.containerOverrides[].environment`), then poll `describe_tasks`
  to `STOPPED` and assert exit code 0 instead of the old `StatusCode == 200`. Update
  `environment.py` (boto client `lambda` → `ecs`) too. Keep it CI-disabled as today.
- **Component tests — no change needed (verified).** The only reference,
  `tests/component/steps/onboarding_steps.py:71-72`, merely *seeds* the
  `player-stats/sleeper_nfl_player_stats.json` S3 object (via the `player_stats.json`
  fixture) as onboarding input. This migration doesn't change that object's key or schema,
  so the onboarding component test is unaffected. No component test exercises the refresher
  itself.
- `docs/requirements/backend/BE-011-sleeper-player-stats-refresher.md` — update **first**:
  retitle from "Scheduled Lambda" → "Scheduled ECS Fargate task"; change the trigger from
  S3-event to weekly `cron(15 12 ? * TUE *)`; restate the overrides as **env vars**; drop
  the "must fit within Lambda timeout / process incrementally" edge case (Fargate has no
  15-min cap); note the off-season skip and deep-merge behavior are unchanged.

---

## Critical files
**aws-account-management:** `infrastructure/modules/networking/{main.tf,variables.tf,outputs.tf}`
(new module), `infrastructure/main.tf` (instantiate the module),
`iam/github-actions-dev-role/terraform-dev-role-iam.json`,
`iam/github-actions-prod-role/terraform-prod-role-iam.json`.
**leagueql-app:** `src/sleeper_player_stats_refresher/{handler.py,Dockerfile,requirements.txt}`,
`infrastructure/global/{dev,prod}/main.tf`, `infrastructure/regional/{main.tf,variables.tf}`,
`.github/workflows/build.yaml`, `tests/unit/sleeper_player_stats_refresher/test_handler.py`,
`tests/integration/player_stats/steps/*`,
`docs/requirements/backend/BE-011-sleeper-player-stats-refresher.md`.

## Verification
1. **VPC (aws-account-management):** `terraform plan`/`apply` locally; confirm the
   `networking` module creates the VPC, 2 public subnets, IGW route, SG (no inbound), and S3
   gateway endpoint. Verify every resource carries the 4 standard tags
   (`project/component/environment/managed-by`) plus its discovery tag (`Name` / `tier`).
2. **Image builds:** `docker build -f src/sleeper_player_stats_refresher/Dockerfile ./src`
   locally; run the container with `S3_BUCKET_NAME` + AWS creds + `MAX_PLAYERS=5` +
   `OUTPUT_KEY=player-stats/integration-test/...` and confirm it writes the override key
   without touching the production cache.
3. **Unit tests:** `pipenv run pytest tests/unit/sleeper_player_stats_refresher --cov=src`.
4. **Lint/format:** `pipenv run ruff check --fix . && pipenv run ruff format .`;
   `terraform fmt` in both repos.
5. **End-to-end (dev):** after CI deploys, manually trigger the schedule (or
   `aws ecs run-task` with the dev task def + `MAX_PLAYERS`) and confirm the task reaches
   the Sleeper API, runs past ~15 min if needed, and writes
   `player-stats/sleeper_nfl_player_stats.json`. Confirm CloudWatch logs land in
   `/ecs/leagueql-sleeper-player-stats-refresher-dev`.
6. **Schedule:** verify the `aws_cloudwatch_event_rule` shows
   `schedule_expression = cron(15 12 ? * TUE *)` (UTC) with an ECS Fargate target, and that
   the old S3-event notification on `player-metadata/` is gone.
7. **Failure alarm (prod):** force a non-zero exit (e.g. a bad `OUTPUT_KEY` permission) and
   confirm the `sleeper_stats_task_failed` event rule fires and an email arrives via
   `lambda_alerts` — i.e. the new `aws_sns_topic_policy` grant to `events.amazonaws.com`
   works.
