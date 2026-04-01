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
  timeout              = 30
  log_retention        = 7
  s3_bucket            = "fantasy-football-recap-${var.environment}-bucket-${local.region}-${local.account_id}"
  s3_key               = "lambda-code-artifacts/processor-lambda.zip"

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

module "backend_api" {
  source = "../modules/api-gw"

  api_name             = "fantasy-football-recap-api-${var.environment}-${local.region}"
  api_description      = "API for fantasy football recap app"
  cors_allow_origins   = ["http://localhost:5173"]
  openapi_spec_path    = "${path.module}/../../docs/api/openapi_spec.yaml"
  stage_name           = "${var.environment}-${local.region}"
  lambda_function_name = split(":", module.api_lambda.lambda_arn)[6]
  log_retention_days   = 7
  
  openapi_vars = {
    aws_region = var.aws_region
    lambda_arn = module.api_lambda.lambda_arn
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
  domain_name       = "api.leagueql.com"
  validation_method = "DNS"
  tags = {
    environment = var.environment
    project     = "fantasy-football-recap"
    component   = "api"
    managed-by  = "terraform"
  }
}
