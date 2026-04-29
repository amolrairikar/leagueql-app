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
}

module "onboarder_lambda" {
  source = "../modules/lambda"

  function_name        = "fantasy-football-recap-onboarder-${var.environment}-${local.region}"
  function_description = "Lambda function for onboarding a fantasy football league"
  role_arn             =  var.onboarder_lambda_role_arn
  handler              = "handler.lambda_handler"
  memory_size          = 2048
  timeout              = 30
  log_retention        = 7
  s3_bucket            = "fantasy-football-recap-${var.environment}-bucket-${local.region}-${local.account_id}"
  s3_key               = "lambda-code-artifacts/onboarder-lambda.zip"

  environment_variables = {
    DYNAMODB_TABLE_NAME = "fantasy-football-recap-table-${var.environment}"
    S3_BUCKET_NAME      = "fantasy-football-recap-${var.environment}-bucket-${local.region}-${local.account_id}"
  }

  tags = {
    environment = var.environment
    project     = "fantasy-football-recap"
    component   = "api"
    managed-by  = "terraform"
  }
}

module "processor_lambda" {
  source = "../modules/lambda"

  function_name        = "fantasy-football-recap-processor-${var.environment}-${local.region}"
  function_description = "Lambda function for processing raw fantasy football league data"
  role_arn             =  var.processor_lambda_role_arn
  handler              = "handler.lambda_handler"
  memory_size          = 2048
  timeout              = 120
  log_retention        = 7
  s3_bucket            = "fantasy-football-recap-${var.environment}-bucket-${local.region}-${local.account_id}"
  s3_key               = "lambda-code-artifacts/processor-lambda.zip"

  environment_variables = {
    DYNAMODB_TABLE_NAME = "fantasy-football-recap-table-${var.environment}"
    S3_BUCKET_NAME      = "fantasy-football-recap-${var.environment}-bucket-${local.region}-${local.account_id}"
    ANTHROPIC_API_KEY   = var.anthropic_api_key
  }

  tags = {
    environment = var.environment
    project     = "fantasy-football-recap"
    component   = "api"
    managed-by  = "terraform"
  }
}

module "api_lambda" {
  source = "../modules/lambda"

  function_name        = "fantasy-football-recap-api-${var.environment}-${local.region}"
  function_description = "Lambda function containing API handler for fantasy football recap app"
  role_arn             =  var.api_lambda_role_arn
  handler              = "main.handler"
  memory_size          = 1024
  timeout              = 15
  log_retention        = 7
  s3_bucket            = "fantasy-football-recap-${var.environment}-bucket-${local.region}-${local.account_id}"
  s3_key               = "lambda-code-artifacts/api-lambda.zip"

  environment_variables = {
    DYNAMODB_TABLE_NAME   = "fantasy-football-recap-table-${var.environment}"
    ONBOARDER_LAMBDA_NAME = "fantasy-football-recap-onboarder-${var.environment}-${local.region}"
    S3_BUCKET_NAME        = "fantasy-football-recap-${var.environment}-bucket-${local.region}-${local.account_id}"
  }

  tags = {
    environment = var.environment
    project     = "fantasy-football-recap"
    component   = "api"
    managed-by  = "terraform"
  }
}

module "player_metadata_lambda" {
  source = "../modules/lambda"

  function_name        = "fantasy-football-recap-player-metadata-${var.environment}-${local.region}"
  function_description = "Fetches and caches Sleeper NFL player metadata to S3"
  role_arn             = var.player_metadata_lambda_role_arn
  handler              = "handler.lambda_handler"
  memory_size          = 512
  timeout              = 30
  log_retention        = 7
  s3_bucket            = "fantasy-football-recap-${var.environment}-bucket-${local.region}-${local.account_id}"
  s3_key               = "lambda-code-artifacts/player_metadata-lambda.zip"

  environment_variables = {
    S3_BUCKET_NAME = "fantasy-football-recap-${var.environment}-bucket-${local.region}-${local.account_id}"
  }

  tags = {
    environment = var.environment
    project     = "fantasy-football-recap"
    component   = "api"
    managed-by  = "terraform"
  }
}

resource "aws_cloudwatch_event_rule" "player_metadata_schedule" {
  name                = "player-metadata-refresh-${var.environment}-${local.region}"
  schedule_expression = "cron(0 12 ? * TUE,THU *)"
  state               = local.region == "east" ? "ENABLED" : "DISABLED"

  tags = {
    environment = var.environment
    project     = "fantasy-football-recap"
    component   = "api"
    managed-by  = "terraform"
  }
}

resource "aws_cloudwatch_event_target" "player_metadata_target" {
  rule = aws_cloudwatch_event_rule.player_metadata_schedule.name
  arn  = module.player_metadata_lambda.lambda_arn
}

resource "aws_lambda_permission" "allow_eventbridge_player_metadata" {
  statement_id  = "AllowEventBridgeInvoke"
  action        = "lambda:InvokeFunction"
  function_name = module.player_metadata_lambda.lambda_arn
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.player_metadata_schedule.arn
}

module "sleeper_refresh_orchestrator_lambda" {
  source = "../modules/lambda"

  function_name        = "fantasy-football-recap-sleeper-refresh-orchestrator-${var.environment}-${local.region}"
  function_description = "Lambda function to orchestrate scheduled Sleeper league refreshes"
  role_arn             = var.sleeper_refresh_orchestrator_lambda_role_arn
  handler              = "handler.lambda_handler"
  memory_size          = 512
  timeout              = 60
  log_retention        = 7
  s3_bucket            = "fantasy-football-recap-${var.environment}-bucket-${local.region}-${local.account_id}"
  s3_key               = "lambda-code-artifacts/sleeper_refresh_orchestrator-lambda.zip"

  environment_variables = {
    DYNAMODB_TABLE_NAME   = "fantasy-football-recap-table-${var.environment}"
    ONBOARDER_LAMBDA_NAME = "fantasy-football-recap-onboarder-${var.environment}-${local.region}"
  }

  tags = {
    environment = var.environment
    project     = "fantasy-football-recap"
    component   = "api"
    managed-by  = "terraform"
  }
}

resource "aws_cloudwatch_event_rule" "sleeper_refresh_schedule" {
  name                = "sleeper-refresh-schedule-${var.environment}-${local.region}"
  schedule_expression = "cron(0 13 ? * TUE *)"
  state               = local.region == "east" ? "ENABLED" : "DISABLED"

  tags = {
    environment = var.environment
    project     = "fantasy-football-recap"
    component   = "api"
    managed-by  = "terraform"
  }
}

resource "aws_cloudwatch_event_target" "sleeper_refresh_target" {
  rule = aws_cloudwatch_event_rule.sleeper_refresh_schedule.name
  arn  = module.sleeper_refresh_orchestrator_lambda.lambda_arn
}

resource "aws_lambda_permission" "allow_eventbridge_sleeper_refresh" {
  statement_id  = "AllowEventBridgeInvoke"
  action        = "lambda:InvokeFunction"
  function_name = module.sleeper_refresh_orchestrator_lambda.lambda_arn
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.sleeper_refresh_schedule.arn
}

module "backend_api" {
  source = "../modules/api-gw"

  api_name             = "fantasy-football-recap-api-${var.environment}-${local.region}"
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
    project     = "fantasy-football-recap"
    component   = "api"
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
    project     = "fantasy-football-recap"
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
