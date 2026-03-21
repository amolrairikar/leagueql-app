terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
  }
}

provider "aws" {
  alias  = "primary"
  region = "us-east-1"
}

provider "aws" {
  alias  = "replica"
  region = "us-west-2"
}

locals {
  primary_bucket_arn   = "arn:aws:s3:::fantasy-football-recap-${var.environment}-bucket-east-${var.account_id}"
  secondary_bucket_arn = "arn:aws:s3:::fantasy-football-recap-${var.environment}-bucket-west-${var.account_id}"
}

module "dynamodb" {
  source = "../../modules/dynamodb"

  providers = {
    aws.primary = aws.primary
    aws.replica = aws.replica
  }

  table_name      = "fantasy-football-recap-table-${var.environment}"
  hash_key        = "PK"
  range_key       = "SK"
  replica_regions = ["us-west-2"]
  
  tags = {
    environment = var.environment
    project     = "fantasy-football-recap"
    component   = "database"
    managed-by  = "terraform"
  }
}

module "s3-replication-role" {
  source = "../../modules/iam-role"
  role_name = "fantasy-football-recap-s3-${var.environment}-replication-role"
  role_description = "IAM role for replicating objects between east & west Fantasy Football Recap project prod S3 buckets."
  trust_policy_json = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "s3.amazonaws.com"
        }
      }
    ]
  })
  role_policy_json = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "AllowBucketLevelPermissions"
        Effect = "Allow"
        Action = [
          "s3:GetReplicationConfiguration",
          "s3:ListBucket"
        ]
        Resource = [
          local.primary_bucket_arn,
          local.secondary_bucket_arn
        ]
      },
      {
        Sid    = "AllowObjectLevelPermissions"
        Effect = "Allow"
        Action = [
          "s3:GetObjectVersionForReplication",
          "s3:GetObjectVersionAcl",
          "s3:GetObjectVersionTagging",
          "s3:ReplicateObject",
          "s3:ReplicateDelete",
          "s3:ReplicateTags"
        ]
        Resource = [
          "${local.primary_bucket_arn}/*",
          "${local.secondary_bucket_arn}/*"
        ]
      }
    ]
  })

  tags = {
    environment = var.environment
    project     = "fantasy-football-recap"
    component   = "s3"
    managed-by  = "terraform"
  }
}

module "s3-bidirectional-replication" {
  source = "../../modules/s3"

  providers = {
    aws.primary = aws.primary
    aws.replica = aws.replica
  }

  bucket_prefix        = "fantasy-football-recap-${var.environment}-bucket"
  account_id           = var.account_id
  primary_aws_region   = "us-east-1"
  secondary_aws_region = "us-west-2"
  versioning_enabled   = true  
  replication_role_arn = module.s3-replication-role.role_arn

  lifecycle_rules = [{
    rule_name       = "expire-noncurrent-objects"
    prefix          = "lambda-code-artifacts/"
    noncurrent_days = 7
  }]

  tags = {
    environment = var.environment
    project     = "fantasy-football-recap"
    component   = "s3"
    managed-by  = "terraform"
  }
}

module "onboarding-lambda-role" {
  source = "../../modules/iam-role"
  role_name = "fantasy-football-recap-onboarding-lambda-${var.environment}-role"
  role_description = "Execution role for onboarding lambda."
  trust_policy_json = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })
  role_policy_json = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "CreateLogGroups"
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup"
        ]
        Resource = [
          "arn:aws:logs:us-east-1:${var.account_id}:*",
          "arn:aws:logs:us-west-2:${var.account_id}:*"
        ]
      },
      {
        Sid    = "CreateLogEvents"
        Effect = "Allow"
        Action = [
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ],
        Resource = [
          "arn:aws:logs:us-east-1:${var.account_id}:log-group:/aws/lambda/fantasy-football-recap-onboarder-${var.environment}-east:*",
          "arn:aws:logs:us-west-2:${var.account_id}:log-group:/aws/lambda/fantasy-football-recap-onboarder-${var.environment}-west:*"
        ]
      },
      {
        Sid    = "WriteToDynamoDB"
        Effect = "Allow"
        Action = [
          "dynamodb:PutItem",
          "dynamodb:BatchWriteItem",
          "dynamodb:UpdateItem"
        ]
        Resource = [module.dynamodb.primary_table_arn]
      }
    ]
  })

  tags = {
    environment = var.environment
    project     = "fantasy-football-recap"
    component   = "api"
    managed-by  = "terraform"
  }
}

module "api-lambda-role" {
  source = "../../modules/iam-role"
  role_name = "fantasy-football-recap-api-lambda-${var.environment}-role"
  role_description = "Execution role for API lambda."
  trust_policy_json = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })
  role_policy_json = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "CreateLogGroups"
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup"
        ]
        Resource = [
          "arn:aws:logs:us-east-1:${var.account_id}:*",
          "arn:aws:logs:us-west-2:${var.account_id}:*"
        ]
      },
      {
        Sid    = "CreateLogEvents"
        Effect = "Allow"
        Action = [
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ],
        Resource = [
          "arn:aws:logs:us-east-1:${var.account_id}:log-group:/aws/lambda/fantasy-football-recap-api-${var.environment}-east:*",
          "arn:aws:logs:us-west-2:${var.account_id}:log-group:/aws/lambda/fantasy-football-recap-api-${var.environment}-west:*"
        ]
      },
      {
        Sid    = "CRUDDynamoDB"
        Effect = "Allow"
        Action = [
          "dynamodb:PutItem",
          "dynamodb:BatchWriteItem",
          "dynamodb:UpdateItem",
          "dynamodb:GetItem",
          "dynamodb:BatchGetItem",
          "dynamodb:Query",
          "dynamodb:Scan",
          "dynamodb:DeleteItem"
        ]
        Resource = [module.dynamodb.primary_table_arn]
      }
    ]
  })

  tags = {
    environment = var.environment
    project     = "fantasy-football-recap"
    component   = "api"
    managed-by  = "terraform"
  }
}

module "api-gateway-role" {
  source = "../../modules/iam-role"
  role_name = "fantasy-football-recap-api-gateway-${var.environment}-role"
  role_description = "Role for API Gateway to write logs to Cloudwatch."
  trust_policy_json = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "apigateway.amazonaws.com"
        }
      }
    ]
  })
  role_policy_json = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "CreateLogGroups"
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:DescribeLogGroups",
        ]
        Resource = [
          "arn:aws:logs:us-east-1:${var.account_id}:*",
          "arn:aws:logs:us-west-2:${var.account_id}:*"
        ]
      },
      {
        Sid    = "CreateLogEvents"
        Effect = "Allow"
        Action = [
          "logs:CreateLogStream",
          "logs:GetLogEvents",
          "logs:PutLogEvents",
          "logs:FilterLogEvents",
          "logs:DescribeLogStreams"
        ],
        Resource = [
          "arn:aws:logs:us-east-1:${var.account_id}:log-group:/aws/apigateway/fantasy-football-recap-api-${var.environment}-east:*",
          "arn:aws:logs:us-west-2:${var.account_id}:log-group:/aws/apigateway/fantasy-football-recap-api-${var.environment}-west:*"
        ]
      }
    ]
  })

  tags = {
    environment = var.environment
    project     = "fantasy-football-recap"
    component   = "api"
    managed-by  = "terraform"
  }
}
