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
  onboarder_role_arn = "arn:aws:iam::${local.account_id}:role/leagueql-${var.environment}-onboarder-role"
  processor_role_arn = "arn:aws:iam::${local.account_id}:role/leagueql-${var.environment}-onboarding-processor-role"
  api_role_arn = "arn:aws:iam::${local.account_id}:role/leagueql-${var.environment}-api-role"
  player_metadata_role_arn = "arn:aws:iam::${local.account_id}:role/leagueql-${var.environment}-sleeper-player-metadata-fetcher-role"
  sleeper_refresh_role_arn = "arn:aws:iam::${local.account_id}:role/leagueql-${var.environment}-sleeper-league-refresh-role"
  sleeper_player_stats_refresher_role_arn = "arn:aws:iam::${local.account_id}:role/leagueql-${var.environment}-sleeper-player-stats-refresher-role"
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
  memory_size          = 1024
  timeout              = 15
  log_retention        = 7
  s3_bucket            = "leagueql-${var.environment}-bucket-${local.region}-${local.account_id}"
  s3_key               = "lambda-code-artifacts/api-lambda.zip"

  environment_variables = {
    DYNAMODB_TABLE_NAME   = "leagueql-table-${var.environment}"
    ONBOARDER_LAMBDA_NAME = "leagueql-onboarder-${var.environment}"
    S3_BUCKET_NAME        = "leagueql-${var.environment}-bucket-${local.region}-${local.account_id}"
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
  cors_allow_origins   = ["http://localhost:5173", "https://leagueql.com"]
  openapi_spec_path    = "${path.module}/../../docs/api/openapi_spec.yaml"
  stage_name           = "${var.environment}-${local.region}"
  lambda_function_name = split(":", module.api_lambda.lambda_arn)[6]
  log_retention_days   = 7
  clerk_issuer_url     = var.clerk_issuer_url
  clerk_jwt_audience   = var.clerk_jwt_audience 
  
  openapi_vars = {
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

module "sleeper_player_stats_refresher_lambda" {
  source = "../modules/lambda"
  count  = local.region == "east" ? 1 : 0

  function_name        = "leagueql-sleeper-player-stats-refresher-${var.environment}"
  function_description = "Fetches stats for all active NFL players from Sleeper API and writes to S3"
  role_arn             = local.sleeper_player_stats_refresher_role_arn
  handler              = "handler.lambda_handler"
  memory_size          = 512
  timeout              = 300
  log_retention        = 7
  s3_bucket            = "leagueql-${var.environment}-bucket-${local.region}-${local.account_id}"
  s3_key               = "lambda-code-artifacts/sleeper_player_stats_refresher-lambda.zip"

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

resource "aws_sns_topic_subscription" "lambda_alerts_email" {
  count     = var.environment == "prod" ? 1 : 0
  topic_arn = aws_sns_topic.lambda_alerts[0].arn
  protocol  = "email"
  endpoint  = "arairikar1@gmail.com"
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

resource "aws_cloudwatch_metric_alarm" "player_stats_refresher_errors" {
  count               = local.region == "east" && var.environment == "prod" ? 1 : 0
  alarm_name          = "leagueql-sleeper-player-stats-refresher-${var.environment}-errors"
  comparison_operator = "GreaterThanOrEqualToThreshold"
  evaluation_periods  = 1
  metric_name         = "Errors"
  namespace           = "AWS/Lambda"
  period              = 300
  statistic           = "Sum"
  threshold           = 1
  alarm_description   = "Player stats refresher Lambda error detected"
  alarm_actions       = [aws_sns_topic.lambda_alerts[0].arn]
  ok_actions          = [aws_sns_topic.lambda_alerts[0].arn]
  treat_missing_data  = "notBreaching"

  dimensions = {
    FunctionName = "leagueql-sleeper-player-stats-refresher-${var.environment}"
  }

  tags = {
    environment = var.environment
    project     = "leagueql"
    component   = "monitoring"
    managed-by  = "terraform"
  }
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
  threshold           = 3000
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
          "arn:aws:logs:us-east-1:${local.account_id}:log-group:/aws/apigateway/*",
          "arn:aws:logs:us-west-2:${local.account_id}:log-group:/aws/apigateway/*"
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
