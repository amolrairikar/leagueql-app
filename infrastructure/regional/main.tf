terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

data "aws_caller_identity" "current" {}

locals {
  region     = element(split("-", var.aws_region), 1)
  account_id = data.aws_caller_identity.current.account_id

  # Role ARNs constructed from global role names
  onboarder_role_arn        = "arn:aws:iam::${local.account_id}:role/leagueql-${var.environment}-onboarder-role"
  processor_role_arn        = "arn:aws:iam::${local.account_id}:role/leagueql-${var.environment}-onboarding-processor-role"
  api_role_arn              = "arn:aws:iam::${local.account_id}:role/leagueql-${var.environment}-api-role"
  player_metadata_role_arn  = "arn:aws:iam::${local.account_id}:role/leagueql-${var.environment}-sleeper-player-metadata-fetcher-role"
  sleeper_refresh_role_arn  = "arn:aws:iam::${local.account_id}:role/leagueql-${var.environment}-sleeper-league-refresh-role"
  discord_notifier_role_arn = "arn:aws:iam::${local.account_id}:role/leagueql-${var.environment}-discord-notifier-role"

  # Sleeper player stats refresher runs as a Fargate task (see BE-011). Roles are
  # created in infrastructure/global; ARNs are reconstructed here from their names.
  sleeper_stats_task_role_arn      = "arn:aws:iam::${local.account_id}:role/leagueql-${var.environment}-sleeper-player-stats-refresher-task-role"
  sleeper_stats_task_exec_role_arn = "arn:aws:iam::${local.account_id}:role/leagueql-${var.environment}-sleeper-stats-task-exec-role"
  sleeper_stats_events_role_arn    = "arn:aws:iam::${local.account_id}:role/leagueql-${var.environment}-sleeper-stats-events-role"
  sleeper_stats_image              = "${local.account_id}.dkr.ecr.${var.aws_region}.amazonaws.com/leagueql-sleeper-player-stats-refresher-${var.environment}:${var.image_tag}"

  # Browser origins allowed by CORS. Production trusts only the live site; dev
  # additionally trusts the local Vite dev server. Shared by the API Gateway CORS
  # config and the API Lambda (FastAPI middleware) so the two never diverge — in
  # particular so production never trusts the local dev origin.
  cors_allow_origins = var.environment == "dev" ? ["http://localhost:5173", "https://leagueql.com"] : ["https://leagueql.com"]
}

module "onboarder_lambda" {
  source = "../modules/lambda"
  count  = local.region == "east" ? 1 : 0

  function_name        = "leagueql-onboarder-${var.environment}"
  function_description = "Lambda function for onboarding a fantasy football league"
  role_arn             = local.onboarder_role_arn
  handler              = "handler.lambda_handler"
  memory_size          = 2048
  timeout              = 30
  log_retention        = 7
  s3_bucket            = "leagueql-${var.environment}-bucket-${local.region}-${local.account_id}"
  s3_key               = "lambda-code-artifacts/onboarder-lambda.zip"

  environment_variables = {
    DYNAMODB_TABLE_NAME = "leagueql-table-${var.environment}"
    S3_BUCKET_NAME      = "leagueql-${var.environment}-bucket-${local.region}-${local.account_id}"
    SNS_TOPIC_ARN       = var.environment == "prod" ? aws_sns_topic.lambda_alerts[0].arn : ""

    # OpenTelemetry trace-context propagation → Axiom (BE-020). A no-op unless set.
    # The ingest token is fetched at runtime from SSM by *name* (value never lands
    # here / in TF state / in CI); dataset is per-env so dev traffic never pollutes
    # prod. ENVIRONMENT tags spans' deployment.environment.
    ENVIRONMENT               = var.environment
    AXIOM_API_TOKEN_SSM_PARAM = "/leagueql/${var.environment}/axiom/api_token"
    AXIOM_DATASET             = "leagueql-${var.environment}"
    AXIOM_TRACES_URL          = "https://api.axiom.co/v1/traces"
  }

  tags = {
    environment = var.environment
    project     = "leagueql"
    component   = "api"
    managed-by  = "terraform"
  }
}

module "processor_lambda" {
  source = "../modules/lambda"
  count  = local.region == "east" ? 1 : 0

  function_name        = "leagueql-processor-${var.environment}"
  function_description = "Lambda function for processing raw fantasy football league data"
  role_arn             = local.processor_role_arn
  handler              = "handler.lambda_handler"
  memory_size          = 2048
  timeout              = 120
  log_retention        = 7
  s3_bucket            = "leagueql-${var.environment}-bucket-${local.region}-${local.account_id}"
  s3_key               = "lambda-code-artifacts/processor-lambda.zip"

  environment_variables = {
    DYNAMODB_TABLE_NAME = "leagueql-table-${var.environment}"
    S3_BUCKET_NAME      = "leagueql-${var.environment}-bucket-${local.region}-${local.account_id}"
    SNS_TOPIC_ARN       = var.environment == "prod" ? aws_sns_topic.lambda_alerts[0].arn : ""

    # OpenTelemetry trace-context propagation → Axiom (BE-020). A no-op unless set.
    # The ingest token is fetched at runtime from SSM by *name* (value never lands
    # here / in TF state / in CI); dataset is per-env so dev traffic never pollutes
    # prod. ENVIRONMENT tags spans' deployment.environment.
    ENVIRONMENT               = var.environment
    AXIOM_API_TOKEN_SSM_PARAM = "/leagueql/${var.environment}/axiom/api_token"
    AXIOM_DATASET             = "leagueql-${var.environment}"
    AXIOM_TRACES_URL          = "https://api.axiom.co/v1/traces"
  }

  tags = {
    environment = var.environment
    project     = "leagueql"
    component   = "api"
    managed-by  = "terraform"
  }
}

module "api_lambda" {
  source = "../modules/lambda"

  function_name        = "leagueql-api-${var.environment}-${local.region}"
  function_description = "Lambda function containing API handler for fantasy football recap app"
  role_arn             = local.api_role_arn
  handler              = "main.handler"
  # 2048 MB ≈ a full vCPU; cold-start init here is CPU-bound (imports), so more
  # CPU shortens both init and warm-request latency. Per-ms cost is higher but
  # duration drops, and the API runs well under its 15s timeout.
  memory_size   = 2048
  timeout       = 15
  log_retention = 7
  s3_bucket     = "leagueql-${var.environment}-bucket-${local.region}-${local.account_id}"
  s3_key        = "lambda-code-artifacts/api-lambda.zip"

  environment_variables = {
    DYNAMODB_TABLE_NAME   = "leagueql-table-${var.environment}"
    ONBOARDER_LAMBDA_NAME = "leagueql-onboarder-${var.environment}"
    S3_BUCKET_NAME        = "leagueql-${var.environment}-bucket-${local.region}-${local.account_id}"
    SNS_TOPIC_ARN         = var.environment == "prod" ? aws_sns_topic.lambda_alerts[0].arn : ""

    # Browser origins the FastAPI CORS middleware trusts, kept in lockstep with the
    # API Gateway CORS config via the shared local (prod excludes the dev origin).
    CORS_ALLOW_ORIGINS = join(",", local.cors_allow_origins)

    # OpenTelemetry tracing → Axiom (BE-020). A no-op unless these are set, so it's
    # safe in every environment. The ingest token is fetched at runtime from SSM by
    # *name* (value never lands here / in TF state / in CI); dataset is per-env so
    # dev/test traffic never pollutes prod. ENVIRONMENT tags spans' deployment.environment.
    ENVIRONMENT               = var.environment
    AXIOM_API_TOKEN_SSM_PARAM = "/leagueql/${var.environment}/axiom/api_token"
    AXIOM_DATASET             = "leagueql-${var.environment}"
    AXIOM_TRACES_URL          = "https://api.axiom.co/v1/traces"

    # Feature flags via SSM Parameter Store (BE-017). Flags are resolved at runtime
    # from this parameter by *name* via ssm:GetParameter (IAM-role access, no secret);
    # the flag values are edited in the SSM console (runtime toggle, no redeploy). With
    # this unset, all flags default off.
    FEATURE_FLAGS_SSM_PARAM = "/leagueql/${var.environment}/feature-flags"
  }

  tags = {
    environment = var.environment
    project     = "leagueql"
    component   = "api"
    managed-by  = "terraform"
  }
}

module "player_metadata_lambda" {
  source = "../modules/lambda"
  count  = local.region == "east" ? 1 : 0

  function_name        = "leagueql-sleeper-player-metadata-${var.environment}"
  function_description = "Fetches and caches Sleeper NFL player metadata to S3"
  role_arn             = local.player_metadata_role_arn
  handler              = "handler.lambda_handler"
  memory_size          = 512
  timeout              = 30
  log_retention        = 7
  s3_bucket            = "leagueql-${var.environment}-bucket-${local.region}-${local.account_id}"
  s3_key               = "lambda-code-artifacts/player_metadata-lambda.zip"

  environment_variables = {
    S3_BUCKET_NAME = "leagueql-${var.environment}-bucket-${local.region}-${local.account_id}"
  }

  tags = {
    environment = var.environment
    project     = "leagueql"
    component   = "api"
    managed-by  = "terraform"
  }
}

resource "aws_cloudwatch_event_rule" "player_metadata_schedule" {
  count               = local.region == "east" ? 1 : 0
  name                = "player-metadata-refresh-${var.environment}-${local.region}"
  schedule_expression = "cron(0 12 ? * TUE,THU *)"
  state               = "ENABLED"

  tags = {
    environment = var.environment
    project     = "leagueql"
    component   = "api"
    managed-by  = "terraform"
  }
}

resource "aws_cloudwatch_event_target" "player_metadata_target" {
  count = local.region == "east" ? 1 : 0
  rule  = aws_cloudwatch_event_rule.player_metadata_schedule[0].name
  arn   = module.player_metadata_lambda[0].lambda_arn
}

resource "aws_lambda_permission" "allow_eventbridge_player_metadata" {
  count         = local.region == "east" ? 1 : 0
  statement_id  = "AllowEventBridgeInvoke"
  action        = "lambda:InvokeFunction"
  function_name = module.player_metadata_lambda[0].lambda_arn
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.player_metadata_schedule[0].arn
}

module "sleeper_refresh_lambda" {
  source = "../modules/lambda"
  count  = local.region == "east" ? 1 : 0

  function_name        = "leagueql-sleeper-refresh-${var.environment}"
  function_description = "Lambda function to schedule Sleeper league refreshes"
  role_arn             = local.sleeper_refresh_role_arn
  handler              = "handler.lambda_handler"
  memory_size          = 512
  timeout              = 60
  log_retention        = 7
  s3_bucket            = "leagueql-${var.environment}-bucket-${local.region}-${local.account_id}"
  s3_key               = "lambda-code-artifacts/sleeper_refresh-lambda.zip"

  environment_variables = {
    DYNAMODB_TABLE_NAME   = "leagueql-table-${var.environment}"
    ONBOARDER_LAMBDA_NAME = "leagueql-onboarder-${var.environment}"

    # OpenTelemetry trace-context propagation → Axiom (BE-020). A no-op unless set.
    # The ingest token is fetched at runtime from SSM by *name* (value never lands
    # here / in TF state / in CI); dataset is per-env so dev traffic never pollutes
    # prod. ENVIRONMENT tags spans' deployment.environment.
    ENVIRONMENT               = var.environment
    AXIOM_API_TOKEN_SSM_PARAM = "/leagueql/${var.environment}/axiom/api_token"
    AXIOM_DATASET             = "leagueql-${var.environment}"
    AXIOM_TRACES_URL          = "https://api.axiom.co/v1/traces"
  }

  tags = {
    environment = var.environment
    project     = "leagueql"
    component   = "api"
    managed-by  = "terraform"
  }
}

resource "aws_cloudwatch_event_rule" "sleeper_refresh_schedule" {
  count               = local.region == "east" ? 1 : 0
  name                = "sleeper-refresh-schedule-${var.environment}-${local.region}"
  schedule_expression = "cron(0 13 ? * TUE *)"
  state               = "ENABLED"

  tags = {
    environment = var.environment
    project     = "leagueql"
    component   = "api"
    managed-by  = "terraform"
  }
}

resource "aws_cloudwatch_event_target" "sleeper_refresh_target" {
  count = local.region == "east" ? 1 : 0
  rule  = aws_cloudwatch_event_rule.sleeper_refresh_schedule[0].name
  arn   = module.sleeper_refresh_lambda[0].lambda_arn
}

resource "aws_lambda_permission" "allow_eventbridge_sleeper_refresh" {
  count         = local.region == "east" ? 1 : 0
  statement_id  = "AllowEventBridgeInvoke"
  action        = "lambda:InvokeFunction"
  function_name = module.sleeper_refresh_lambda[0].lambda_arn
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.sleeper_refresh_schedule[0].arn
}

module "backend_api" {
  source = "../modules/api-gw"

  api_name             = "leagueql-api-${var.environment}-${local.region}"
  api_description      = "API for fantasy football recap app"
  cors_allow_origins   = local.cors_allow_origins
  openapi_spec_path    = "${path.module}/../../docs/api/openapi_spec.yaml"
  stage_name           = "${var.environment}-${local.region}"
  lambda_function_name = split(":", module.api_lambda.lambda_arn)[6]
  log_retention_days   = 7
  clerk_issuer_url     = var.clerk_issuer_url
  clerk_jwt_audience   = var.clerk_jwt_audience

  openapi_vars = {
    # Must match api_name above: API Gateway names the HTTP API from the OpenAPI
    # info.title on (re)import, overriding the resource's name argument.
    api_name           = "leagueql-api-${var.environment}-${local.region}"
    aws_region         = var.aws_region
    lambda_arn         = module.api_lambda.lambda_arn
    clerk_issuer_url   = var.clerk_issuer_url
    clerk_jwt_audience = var.clerk_jwt_audience
  }

  tags = {
    environment = var.environment
    project     = "leagueql"
    component   = "api"
    managed-by  = "terraform"
  }
}

# ── Sleeper player stats refresher: Fargate task (BE-011) ─────────────────────
# A full active-roster refresh fans out one rate-limited request per player and
# regularly exceeds Lambda's 15-minute cap, so it runs as a scheduled Fargate task
# with no execution-time limit. East-only (matches the former Lambda).

# Shared outbound-only VPC discovered by tag (created in aws-account-management).
data "aws_vpc" "fargate" {
  count = local.region == "east" ? 1 : 0
  tags = {
    Name = "leagueql-fargate-vpc"
  }
}

data "aws_subnets" "fargate_public" {
  count = local.region == "east" ? 1 : 0
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.fargate[0].id]
  }
  tags = {
    tier = "public"
  }
}

data "aws_security_group" "fargate_task" {
  count = local.region == "east" ? 1 : 0
  tags = {
    Name = "leagueql-fargate-task-sg"
  }
}

resource "aws_ecs_cluster" "leagueql" {
  count = local.region == "east" ? 1 : 0
  name  = "leagueql-${var.environment}"

  setting {
    name  = "containerInsights"
    value = "disabled"
  }

  tags = {
    environment = var.environment
    project     = "leagueql"
    component   = "data-processing"
    managed-by  = "terraform"
  }
}

resource "aws_cloudwatch_log_group" "sleeper_player_stats_refresher" {
  count             = local.region == "east" ? 1 : 0
  name              = "/ecs/leagueql-sleeper-player-stats-refresher-${var.environment}"
  retention_in_days = 7

  tags = {
    environment = var.environment
    project     = "leagueql"
    component   = "data-processing"
    managed-by  = "terraform"
  }
}

resource "aws_ecs_task_definition" "sleeper_player_stats_refresher" {
  count                    = local.region == "east" ? 1 : 0
  family                   = "leagueql-sleeper-player-stats-refresher-${var.environment}"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = 512
  memory                   = 1024
  execution_role_arn       = local.sleeper_stats_task_exec_role_arn
  task_role_arn            = local.sleeper_stats_task_role_arn

  container_definitions = jsonencode([
    {
      name      = "sleeper-player-stats-refresher"
      image     = local.sleeper_stats_image
      essential = true
      environment = [
        {
          name  = "S3_BUCKET_NAME"
          value = "leagueql-${var.environment}-bucket-${local.region}-${local.account_id}"
        }
      ]
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.sleeper_player_stats_refresher[0].name
          "awslogs-region"        = var.aws_region
          "awslogs-stream-prefix" = "ecs"
        }
      }
    }
  ])

  tags = {
    environment = var.environment
    project     = "leagueql"
    component   = "data-processing"
    managed-by  = "terraform"
  }
}

# Weekly schedule, 15 min after the Tuesday player-metadata refresh so metadata is
# fresh. CloudWatch Events cron is UTC. Replaces the former S3-event trigger.
resource "aws_cloudwatch_event_rule" "sleeper_player_stats_refresh_schedule" {
  count               = local.region == "east" ? 1 : 0
  name                = "sleeper-player-stats-refresh-${var.environment}-${local.region}"
  schedule_expression = "cron(15 12 ? * TUE *)"
  state               = "ENABLED"

  tags = {
    environment = var.environment
    project     = "leagueql"
    component   = "data-processing"
    managed-by  = "terraform"
  }
}

resource "aws_cloudwatch_event_target" "sleeper_player_stats_refresh_target" {
  count    = local.region == "east" ? 1 : 0
  rule     = aws_cloudwatch_event_rule.sleeper_player_stats_refresh_schedule[0].name
  arn      = aws_ecs_cluster.leagueql[0].arn
  role_arn = local.sleeper_stats_events_role_arn

  ecs_target {
    task_definition_arn = aws_ecs_task_definition.sleeper_player_stats_refresher[0].arn
    launch_type         = "FARGATE"
    task_count          = 1

    network_configuration {
      subnets          = data.aws_subnets.fargate_public[0].ids
      security_groups  = [data.aws_security_group.fargate_task[0].id]
      assign_public_ip = true
    }
  }
}

resource "aws_sns_topic" "lambda_alerts" {
  count = var.environment == "prod" ? 1 : 0
  name  = "leagueql-lambda-alerts-${var.environment}-${local.region}"

  tags = {
    environment = var.environment
    project     = "leagueql"
    component   = "monitoring"
    managed-by  = "terraform"
  }
}

# Infra/error alerts are forwarded to a private Discord channel by a small Lambda
# subscriber (below) instead of email. A Lambda is required because Discord webhooks
# accept only a specific JSON body and cannot complete SNS's HTTPS subscription
# confirmation handshake. Deployed per-region so each region's topic feeds Discord.
module "discord_notifier_lambda" {
  source = "../modules/lambda"
  count  = var.environment == "prod" ? 1 : 0

  function_name        = "leagueql-discord-notifier-${var.environment}-${local.region}"
  function_description = "Forwards SNS infra/error alerts to a Discord channel webhook"
  role_arn             = local.discord_notifier_role_arn
  handler              = "handler.lambda_handler"
  memory_size          = 256
  timeout              = 10
  log_retention        = 7
  s3_bucket            = "leagueql-${var.environment}-bucket-${local.region}-${local.account_id}"
  s3_key               = "lambda-code-artifacts/discord_notifier-lambda.zip"

  environment_variables = {
    # Discord webhook URL fetched at runtime from SSM by *name* (the value never
    # lands here / in TF state / in CI).
    DISCORD_WEBHOOK_URL_SSM_PARAM = "/leagueql/${var.environment}/discord/webhook_url"
  }

  tags = {
    environment = var.environment
    project     = "leagueql"
    component   = "monitoring"
    managed-by  = "terraform"
  }
}

resource "aws_lambda_permission" "discord_notifier_sns_invoke" {
  count         = var.environment == "prod" ? 1 : 0
  statement_id  = "AllowSNSInvoke"
  action        = "lambda:InvokeFunction"
  function_name = module.discord_notifier_lambda[0].lambda_arn
  principal     = "sns.amazonaws.com"
  source_arn    = aws_sns_topic.lambda_alerts[0].arn
}

resource "aws_sns_topic_subscription" "lambda_alerts_discord" {
  count     = var.environment == "prod" ? 1 : 0
  topic_arn = aws_sns_topic.lambda_alerts[0].arn
  protocol  = "lambda"
  endpoint  = module.discord_notifier_lambda[0].lambda_arn
}

# Dead-letter queue for onboarder async invocations. The API and the scheduled
# Sleeper refresh invoke the onboarder with InvocationType="Event" (fire-and-forget);
# when an event fails all of Lambda's async retries, AWS would otherwise drop it
# silently. Routing it here preserves the full payload (incl. correlation_id) so a
# poison/failed onboard or refresh can be inspected and replayed. 14-day retention
# is the SQS maximum.
resource "aws_sqs_queue" "onboarder_dlq" {
  count                     = local.region == "east" && var.environment == "prod" ? 1 : 0
  name                      = "leagueql-onboarder-dlq-${var.environment}"
  message_retention_seconds = 1209600
  sqs_managed_sse_enabled   = true

  tags = {
    environment = var.environment
    project     = "leagueql"
    component   = "monitoring"
    managed-by  = "terraform"
  }
}

# Send onboarder async-invocation failures (after retries are exhausted) to the DLQ.
resource "aws_lambda_function_event_invoke_config" "onboarder" {
  count         = local.region == "east" && var.environment == "prod" ? 1 : 0
  function_name = "leagueql-onboarder-${var.environment}"
  # Lambda's default async retry count; transient failures still get retried twice
  # before an event is treated as poison and routed to the DLQ.
  maximum_retry_attempts = 2

  destination_config {
    on_failure {
      destination = aws_sqs_queue.onboarder_dlq[0].arn
    }
  }

  depends_on = [module.onboarder_lambda]
}

# Any message landing in the DLQ means an onboard/refresh was permanently dropped.
# Messages persist (no consumer), so the alarm stays in ALARM until the queue is
# drained, and clears (ok_actions) once the dropped events are handled/replayed.
resource "aws_cloudwatch_metric_alarm" "onboarder_dlq_messages" {
  count               = local.region == "east" && var.environment == "prod" ? 1 : 0
  alarm_name          = "leagueql-onboarder-dlq-${var.environment}-messages"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "ApproximateNumberOfMessagesVisible"
  namespace           = "AWS/SQS"
  period              = 300
  statistic           = "Maximum"
  threshold           = 0
  alarm_description   = "An onboarder async invocation was dropped to the DLQ after exhausting retries"
  alarm_actions       = [aws_sns_topic.lambda_alerts[0].arn]
  ok_actions          = [aws_sns_topic.lambda_alerts[0].arn]
  treat_missing_data  = "notBreaching"

  dimensions = {
    QueueName = aws_sqs_queue.onboarder_dlq[0].name
  }

  tags = {
    environment = var.environment
    project     = "leagueql"
    component   = "monitoring"
    managed-by  = "terraform"
  }
}

resource "aws_cloudwatch_metric_alarm" "onboarder_errors" {
  count               = local.region == "east" && var.environment == "prod" ? 1 : 0
  alarm_name          = "leagueql-onboarder-${var.environment}-errors"
  comparison_operator = "GreaterThanOrEqualToThreshold"
  evaluation_periods  = 1
  metric_name         = "Errors"
  namespace           = "AWS/Lambda"
  period              = 300
  statistic           = "Sum"
  threshold           = 1
  alarm_description   = "Onboarder Lambda error detected"
  alarm_actions       = [aws_sns_topic.lambda_alerts[0].arn]
  ok_actions          = [aws_sns_topic.lambda_alerts[0].arn]
  treat_missing_data  = "notBreaching"

  dimensions = {
    FunctionName = "leagueql-onboarder-${var.environment}"
  }

  tags = {
    environment = var.environment
    project     = "leagueql"
    component   = "monitoring"
    managed-by  = "terraform"
  }
}

resource "aws_cloudwatch_metric_alarm" "processor_errors" {
  count               = local.region == "east" && var.environment == "prod" ? 1 : 0
  alarm_name          = "leagueql-processor-${var.environment}-errors"
  comparison_operator = "GreaterThanOrEqualToThreshold"
  evaluation_periods  = 1
  metric_name         = "Errors"
  namespace           = "AWS/Lambda"
  period              = 300
  statistic           = "Sum"
  threshold           = 1
  alarm_description   = "Processor Lambda error detected"
  alarm_actions       = [aws_sns_topic.lambda_alerts[0].arn]
  ok_actions          = [aws_sns_topic.lambda_alerts[0].arn]
  treat_missing_data  = "notBreaching"

  dimensions = {
    FunctionName = "leagueql-processor-${var.environment}"
  }

  tags = {
    environment = var.environment
    project     = "leagueql"
    component   = "monitoring"
    managed-by  = "terraform"
  }
}

resource "aws_cloudwatch_metric_alarm" "sleeper_refresh_errors" {
  count               = local.region == "east" && var.environment == "prod" ? 1 : 0
  alarm_name          = "leagueql-sleeper-refresh-${var.environment}-errors"
  comparison_operator = "GreaterThanOrEqualToThreshold"
  evaluation_periods  = 1
  metric_name         = "Errors"
  namespace           = "AWS/Lambda"
  period              = 300
  statistic           = "Sum"
  threshold           = 1
  alarm_description   = "Sleeper refresh Lambda error detected"
  alarm_actions       = [aws_sns_topic.lambda_alerts[0].arn]
  ok_actions          = [aws_sns_topic.lambda_alerts[0].arn]
  treat_missing_data  = "notBreaching"

  dimensions = {
    FunctionName = "leagueql-sleeper-refresh-${var.environment}"
  }

  tags = {
    environment = var.environment
    project     = "leagueql"
    component   = "monitoring"
    managed-by  = "terraform"
  }
}

resource "aws_cloudwatch_metric_alarm" "player_metadata_errors" {
  count               = local.region == "east" && var.environment == "prod" ? 1 : 0
  alarm_name          = "leagueql-sleeper-player-metadata-${var.environment}-errors"
  comparison_operator = "GreaterThanOrEqualToThreshold"
  evaluation_periods  = 1
  metric_name         = "Errors"
  namespace           = "AWS/Lambda"
  period              = 300
  statistic           = "Sum"
  threshold           = 1
  alarm_description   = "Player metadata Lambda error detected"
  alarm_actions       = [aws_sns_topic.lambda_alerts[0].arn]
  ok_actions          = [aws_sns_topic.lambda_alerts[0].arn]
  treat_missing_data  = "notBreaching"

  dimensions = {
    FunctionName = "leagueql-sleeper-player-metadata-${var.environment}"
  }

  tags = {
    environment = var.environment
    project     = "leagueql"
    component   = "monitoring"
    managed-by  = "terraform"
  }
}

# A one-shot Fargate task emits no per-run "Errors" metric, so failure monitoring is
# event-based: match ECS Task State Change events for this task definition that stopped
# either with a non-zero container exit code or a start failure (image pull, networking,
# etc., where no exitCode is emitted), and notify via the existing alerts topic.
resource "aws_cloudwatch_event_rule" "sleeper_stats_task_failed" {
  count       = local.region == "east" && var.environment == "prod" ? 1 : 0
  name        = "leagueql-sleeper-player-stats-refresher-${var.environment}-task-failed"
  description = "Sleeper player stats refresher Fargate task failed"

  event_pattern = jsonencode({
    source      = ["aws.ecs"]
    detail-type = ["ECS Task State Change"]
    detail = {
      clusterArn        = [aws_ecs_cluster.leagueql[0].arn]
      taskDefinitionArn = [{ prefix = "${aws_ecs_task_definition.sleeper_player_stats_refresher[0].arn_without_revision}:" }]
      lastStatus        = ["STOPPED"]
      "$or" = [
        { containers = { exitCode = [{ "anything-but" = 0 }] } },
        { stopCode = ["TaskFailedToStart"] }
      ]
    }
  })

  tags = {
    environment = var.environment
    project     = "leagueql"
    component   = "monitoring"
    managed-by  = "terraform"
  }
}

resource "aws_cloudwatch_event_target" "sleeper_stats_task_failed_sns" {
  count = local.region == "east" && var.environment == "prod" ? 1 : 0
  rule  = aws_cloudwatch_event_rule.sleeper_stats_task_failed[0].name
  arn   = aws_sns_topic.lambda_alerts[0].arn
}

# Unlike CloudWatch alarm actions, EventBridge must be explicitly granted publish on
# the topic, otherwise the notification silently fails to deliver.
resource "aws_sns_topic_policy" "lambda_alerts_eventbridge" {
  count = local.region == "east" && var.environment == "prod" ? 1 : 0
  arn   = aws_sns_topic.lambda_alerts[0].arn

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid       = "AllowEventBridgePublish"
        Effect    = "Allow"
        Principal = { Service = "events.amazonaws.com" }
        Action    = "SNS:Publish"
        Resource  = aws_sns_topic.lambda_alerts[0].arn
        Condition = {
          ArnEquals = {
            "aws:SourceArn" = [
              aws_cloudwatch_event_rule.sleeper_stats_task_failed[0].arn,
            ]
          }
        }
      }
    ]
  })
}

resource "aws_cloudwatch_metric_alarm" "api_lambda_errors" {
  count               = var.environment == "prod" ? 1 : 0
  alarm_name          = "leagueql-api-${var.environment}-${local.region}-errors"
  comparison_operator = "GreaterThanOrEqualToThreshold"
  evaluation_periods  = 1
  metric_name         = "Errors"
  namespace           = "AWS/Lambda"
  period              = 300
  statistic           = "Sum"
  threshold           = 1
  alarm_description   = "API Lambda error detected"
  alarm_actions       = [aws_sns_topic.lambda_alerts[0].arn]
  ok_actions          = [aws_sns_topic.lambda_alerts[0].arn]
  treat_missing_data  = "notBreaching"

  dimensions = {
    FunctionName = "leagueql-api-${var.environment}-${local.region}"
  }

  tags = {
    environment = var.environment
    project     = "leagueql"
    component   = "monitoring"
    managed-by  = "terraform"
  }
}

resource "aws_cloudwatch_metric_alarm" "api_gw_5xx" {
  count               = var.environment == "prod" ? 1 : 0
  alarm_name          = "leagueql-api-gw-${var.environment}-${local.region}-5xx"
  comparison_operator = "GreaterThanOrEqualToThreshold"
  evaluation_periods  = 1
  metric_name         = "5XXError"
  namespace           = "AWS/ApiGateway"
  period              = 300
  statistic           = "Sum"
  threshold           = 3
  alarm_description   = "API Gateway 5xx errors exceeded threshold"
  alarm_actions       = [aws_sns_topic.lambda_alerts[0].arn]
  ok_actions          = [aws_sns_topic.lambda_alerts[0].arn]
  treat_missing_data  = "notBreaching"

  dimensions = {
    ApiId = module.backend_api.api_id
  }

  tags = {
    environment = var.environment
    project     = "leagueql"
    component   = "monitoring"
    managed-by  = "terraform"
  }
}

resource "aws_cloudwatch_metric_alarm" "dynamodb_write_spike" {
  count               = local.region == "east" && var.environment == "prod" ? 1 : 0
  alarm_name          = "leagueql-dynamodb-${var.environment}-write-spike"
  comparison_operator = "GreaterThanOrEqualToThreshold"
  evaluation_periods  = 1
  metric_name         = "ConsumedWriteCapacityUnits"
  namespace           = "AWS/DynamoDB"
  period              = 300
  statistic           = "Sum"
  threshold           = 30000
  alarm_description   = "DynamoDB write capacity spike detected"
  alarm_actions       = [aws_sns_topic.lambda_alerts[0].arn]
  ok_actions          = [aws_sns_topic.lambda_alerts[0].arn]
  treat_missing_data  = "notBreaching"

  dimensions = {
    TableName = "leagueql-table-${var.environment}"
  }

  tags = {
    environment = var.environment
    project     = "leagueql"
    component   = "monitoring"
    managed-by  = "terraform"
  }
}

resource "aws_cloudwatch_metric_alarm" "dynamodb_read_spike" {
  count               = local.region == "east" && var.environment == "prod" ? 1 : 0
  alarm_name          = "leagueql-dynamodb-${var.environment}-read-spike"
  comparison_operator = "GreaterThanOrEqualToThreshold"
  evaluation_periods  = 1
  metric_name         = "ConsumedReadCapacityUnits"
  namespace           = "AWS/DynamoDB"
  period              = 300
  statistic           = "Sum"
  threshold           = 25000
  alarm_description   = "DynamoDB read capacity spike detected"
  alarm_actions       = [aws_sns_topic.lambda_alerts[0].arn]
  ok_actions          = [aws_sns_topic.lambda_alerts[0].arn]
  treat_missing_data  = "notBreaching"

  dimensions = {
    TableName = "leagueql-table-${var.environment}"
  }

  tags = {
    environment = var.environment
    project     = "leagueql"
    component   = "monitoring"
    managed-by  = "terraform"
  }
}

resource "aws_cloudwatch_log_resource_policy" "apigateway_log_delivery" {
  policy_name = "api-gateway-log-delivery-${var.environment}"

  policy_document = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "AllowLogDeliveryService"
        Effect = "Allow"
        Principal = {
          Service = "delivery.logs.amazonaws.com"
        }
        Action = [
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = [
          "arn:aws:logs:us-east-1:${local.account_id}:log-group:/aws/apigateway/leagueql-api-${var.environment}-east:*",
          "arn:aws:logs:us-west-2:${local.account_id}:log-group:/aws/apigateway/leagueql-api-${var.environment}-west:*"
        ]
      }
    ]
  })
}

resource "aws_acm_certificate" "api_subdomain_cert" {
  count             = var.environment == "prod" ? 1 : 0
  domain_name       = "api.leagueql.com"
  validation_method = "DNS"

  tags = {
    environment = var.environment
    project     = "leagueql"
    component   = "api"
    managed-by  = "terraform"
  }
}

resource "aws_apigatewayv2_domain_name" "api_subdomain" {
  count       = var.environment == "prod" ? 1 : 0
  domain_name = "api.leagueql.com"

  domain_name_configuration {
    certificate_arn = aws_acm_certificate.api_subdomain_cert[0].arn
    endpoint_type   = "REGIONAL"
    security_policy = "TLS_1_2"
  }
}

resource "aws_apigatewayv2_api_mapping" "api_subdomain_mapping" {
  count       = var.environment == "prod" ? 1 : 0
  api_id      = module.backend_api.api_id
  domain_name = aws_apigatewayv2_domain_name.api_subdomain[0].id
  stage       = "$default"
}

