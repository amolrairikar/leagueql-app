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

module "lambda" {
  source = "../modules/lambda"

  function_name        = "fantasy-football-recap-onboarder-${var.environment}-${local.region}"
  function_description = "Lambda function for onboarding a fantasy football league"
  role_arn             =  var.lambda_role_arn
  handler              = "handler.lambda_handler"
  memory_size          = 2048
  timeout              = 30
  log_retention        = 7
  s3_bucket            = "fantasy-football-recap-${var.environment}-bucket-${local.region}-${local.account_id}"
  s3_key               = "lambda-code-artifacts/onboarder-lambda.zip"

  tags = {
    environment = var.environment
    project     = "fantasy-football-recap"
    component   = "api"
    managed-by  = "terraform"
  }
}