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

module "dynamodb" {
  source = "../../modules/dynamodb"

  providers = {
    aws.primary = aws.primary
    aws.replica = aws.replica
  }

  table_name      = "fantasy-football-recap-table-dev"
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
  role_description = "IAM role for replicating objects between east & west Fantasy Football Recap project dev S3 buckets."
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
          "arn:aws:s3:::fantasy-football-recap-${var.environment}-bucket-east-${var.account_id}",
          "arn:aws:s3:::fantasy-football-recap-${var.environment}-bucket-west-${var.account_id}"
        ]
      },
      {
        Sid    = "AllowObjectLevelPermissions"
        Effect = "Allow"
        Action = [
          "s3:GetObjectVersion*",
          "s3:Replicate*"
        ]
        Resource = [
          "arn:aws:s3:::fantasy-football-recap-${var.environment}-bucket-east-${var.account_id}/*",
          "arn:aws:s3:::fantasy-football-recap-${var.environment}-bucket-west-${var.account_id}/*"
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
    aws.primary   = aws.primary
    aws.secondary = aws.replica
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