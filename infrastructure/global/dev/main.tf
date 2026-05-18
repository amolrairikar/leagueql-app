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
  primary_bucket_arn   = "arn:aws:s3:::leagueql-${var.environment}-bucket-east-${var.account_id}"
  secondary_bucket_arn = "arn:aws:s3:::leagueql-${var.environment}-bucket-west-${var.account_id}"
}

module "dynamodb" {
  source = "../../modules/dynamodb"

  providers = {
    aws.primary = aws.primary
    aws.replica = aws.replica
  }

  table_name      = "leagueql-table-${var.environment}"
  hash_key        = "PK"
  range_key       = "SK"
  replica_regions = ["us-west-2"]
  
  tags = {
    environment = var.environment
    project     = "leagueql"
    component   = "database"
    managed-by  = "terraform"
  }
}

module "s3-replication-role" {
  source = "../../modules/iam-role"
  role_name = "leagueql-s3-${var.environment}-replication-role"
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
    project     = "leagueql"
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

  bucket_prefix        = "leagueql-${var.environment}-bucket"
  account_id           = var.account_id
  primary_aws_region   = "us-east-1"
  secondary_aws_region = "us-west-2"
  versioning_enabled   = true
  replication_role_arn = module.s3-replication-role.role_arn

  lifecycle_rules = [
    {
      rule_name       = "expire-noncurrent-objects"
      prefix          = "lambda-code-artifacts/"
      noncurrent_days = 2
    },
    {
      rule_name       = "expire-noncurrent-api-data"
      prefix          = "raw-api-data/"
      noncurrent_days = 2
    }
  ]

  primary_event_notifications = [
    {
      lambda_function_arn = "arn:aws:lambda:us-east-1:${var.account_id}:function:leagueql-processor-${var.environment}"
      events              = ["s3:ObjectCreated:*"]
      filter_prefix       = "raw-api-data/"
      filter_suffix       = "manifest.json"
    },
    {
      lambda_function_arn = "arn:aws:lambda:us-east-1:${var.account_id}:function:leagueql-sleeper-player-stats-refresher-${var.environment}"
      events              = ["s3:ObjectCreated:Put"]
      filter_prefix       = "player-metadata/"
      filter_suffix       = "sleeper_nfl_players.json"
    }
  ]

  tags = {
    environment = var.environment
    project     = "leagueql"
    component   = "s3"
    managed-by  = "terraform"
  }
}

module "onboarding-lambda-role" {
  source = "../../modules/iam-role"
  role_name = "leagueql-${var.environment}-onboarder-role"
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
          "arn:aws:logs:us-east-1:${var.account_id}:*"
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
          "arn:aws:logs:us-east-1:${var.account_id}:log-group:/aws/lambda/leagueql-onboarder-${var.environment}:*"
        ]
      },
      {
        Sid    = "S3ListBucket"
        Effect = "Allow"
        Action = [
          "s3:ListBucket",
          "s3:ListBucketVersions"
        ],
        Resource = [
          local.primary_bucket_arn
        ]
      },
      {
        Sid    = "ReadFromS3RawPrefix"
        Effect = "Allow"
        Action = [
          "s3:GetObject",
        ]
        Resource = [
          "${local.primary_bucket_arn}/raw-api-data/*"
        ]
      },
      {
        Sid    = "WriteToS3RawPrefix"
        Effect = "Allow"
        Action = [
          "s3:PutObject",
          "s3:PutObjectAcl"
        ]
        Resource = [
          "${local.primary_bucket_arn}/raw-api-data/*"
        ]
      },
      {
        Sid    = "ReadWriteDynamoDB"
        Effect = "Allow"
        Action = [
          "dynamodb:GetItem",
          "dynamodb:PutItem",
          "dynamodb:UpdateItem",
        ]
        Resource = [
          module.dynamodb.primary_table_arn
        ]
      }
    ]
  })

  tags = {
    environment = var.environment
    project     = "leagueql"
    component   = "data-processing"
    managed-by  = "terraform"
  }
}

module "processing-lambda-role" {
  source = "../../modules/iam-role"
  role_name = "leagueql-${var.environment}-onboarding-processor-role"
  role_description = "Execution role for data processing lambda."
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
          "arn:aws:logs:us-east-1:${var.account_id}:*"
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
          "arn:aws:logs:us-east-1:${var.account_id}:log-group:/aws/lambda/leagueql-processor-${var.environment}:*"
        ]
      },
      {
        Sid    = "WriteDynamoDB"
        Effect = "Allow"
        Action = [
          "dynamodb:PutItem",
          "dynamodb:BatchWriteItem",
          "dynamodb:UpdateItem",
          "dynamodb:GetItem"
        ]
        Resource = [
          module.dynamodb.primary_table_arn
        ]
      },
      {
        Sid    = "S3ListBucket"
        Effect = "Allow"
        Action = [
          "s3:ListBucket",
          "s3:ListBucketVersions"
        ],
        Resource = [
          local.primary_bucket_arn
        ]
      },
      {
        Sid    = "ReadFromS3RawPrefix"
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:GetObjectVersion",
        ]
        Resource = [
          "${local.primary_bucket_arn}/raw-api-data/*"
        ]
      },
      {
        Sid    = "ReadFromS3PlayerMetadataPrefix"
        Effect = "Allow"
        Action = [
          "s3:GetObject",
        ]
        Resource = [
          "${local.primary_bucket_arn}/player-metadata/*"
        ]
      },
      {
        Sid    = "ReadFromS3PlayerStatsPrefix"
        Effect = "Allow"
        Action = [
          "s3:GetObject",
        ]
        Resource = [
          "${local.primary_bucket_arn}/player-stats/*"
        ]
      }
    ]
  })

  tags = {
    environment = var.environment
    project     = "leagueql"
    component   = "data-processing"
    managed-by  = "terraform"
  }
}

module "player-metadata-lambda-role" {
  source = "../../modules/iam-role"
  role_name = "leagueql-${var.environment}-sleeper-player-metadata-fetcher-role"
  role_description = "Execution role for Sleeper player data fetcher lambda."
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
          "arn:aws:logs:us-east-1:${var.account_id}:*"
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
          "arn:aws:logs:us-east-1:${var.account_id}:log-group:/aws/lambda/leagueql-sleeper-player-metadata-${var.environment}:*"
        ]
      },
      {
        Sid    = "WriteToS3PlayerMetadataPrefix"
        Effect = "Allow"
        Action = [
          "s3:PutObject",
          "s3:PutObjectAcl"
        ]
        Resource = [
          "${local.primary_bucket_arn}/player-metadata/*"
        ]
      }
    ]
  })

  tags = {
    environment = var.environment
    project     = "leagueql"
    component   = "data-processing"
    managed-by  = "terraform"
  }
}

module "api-lambda-role" {
  source = "../../modules/iam-role"
  role_name = "leagueql-${var.environment}-api-role"
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
          "arn:aws:logs:us-east-1:${var.account_id}:log-group:/aws/lambda/leagueql-api-${var.environment}-east:*",
          "arn:aws:logs:us-west-2:${var.account_id}:log-group:/aws/lambda/leagueql-api-${var.environment}-west:*"
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
          "dynamodb:DeleteItem",
          "dynamodb:ConditionCheckItem"
        ]
        Resource = [
          module.dynamodb.primary_table_arn,
          module.dynamodb.replica_table_arn,
          "${module.dynamodb.primary_table_arn}/index/GSI1",
          "${module.dynamodb.replica_table_arn}/index/GSI1"
        ]
      },
      {
        Sid    = "InvokeOnboarderLambda"
        Effect = "Allow"
        Action = [
          "lambda:InvokeFunction"
        ]
        Resource = [
          "arn:aws:lambda:us-east-1:${var.account_id}:function:leagueql-onboarder-${var.environment}"
        ]
      },
      {
        Sid    = "S3ListBucket"
        Effect = "Allow"
        Action = ["s3:ListBucket"]
        Resource = [
          local.primary_bucket_arn,
          local.secondary_bucket_arn
        ]
      },
      {
        Sid    = "S3DeleteRawDataOnly"
        Effect = "Allow"
        Action = ["s3:DeleteObject"]
        Resource = [
          "${local.primary_bucket_arn}/raw-api-data/*",
          "${local.secondary_bucket_arn}/raw-api-data/*"
        ]
      }
    ]
  })

  tags = {
    environment = var.environment
    project     = "leagueql"
    component   = "api"
    managed-by  = "terraform"
  }
}

module "api-gateway-role" {
  source = "../../modules/iam-role"
  role_name = "leagueql-api-gateway-${var.environment}-role"
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
          "arn:aws:logs:us-east-1:${var.account_id}:log-group:/aws/apigateway/leagueql-api-${var.environment}-east:*",
          "arn:aws:logs:us-west-2:${var.account_id}:log-group:/aws/apigateway/leagueql-api-${var.environment}-west:*"
        ]
      }
    ]
  })

  tags = {
    environment = var.environment
    project     = "leagueql"
    component   = "api"
    managed-by  = "terraform"
  }
}

module "sleeper-player-stats-refresher-lambda-role" {
  source = "../../modules/iam-role"
  role_name = "leagueql-${var.environment}-sleeper-player-stats-refresher-role"
  role_description = "Execution role for Sleeper player stats refresher lambda."
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
          "arn:aws:logs:us-east-1:${var.account_id}:*"
        ]
      },
      {
        Sid    = "CreateLogEvents"
        Effect = "Allow"
        Action = [
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = [
          "arn:aws:logs:us-east-1:${var.account_id}:log-group:/aws/lambda/leagueql-sleeper-player-stats-refresher-${var.environment}:*"
        ]
      },
      {
        Sid    = "ReadPlayerMetadata"
        Effect = "Allow"
        Action = [
          "s3:GetObject"
        ]
        Resource = [
          "${local.primary_bucket_arn}/player-metadata/*"
        ]
      },
      {
        Sid    = "WritePlayerStats"
        Effect = "Allow"
        Action = [
          "s3:PutObject"
        ]
        Resource = [
          "${local.primary_bucket_arn}/player-stats/sleeper_nfl_player_stats.json"
        ]
      }
    ]
  })

  tags = {
    environment = var.environment
    project     = "leagueql"
    component   = "data-processing"
    managed-by  = "terraform"
  }
}

module "sleeper-refresh-lambda-role" {
  source = "../../modules/iam-role"
  role_name = "leagueql-${var.environment}-sleeper-league-refresh-role"
  role_description = "Execution role for Sleeper refresh lambda."
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
          "arn:aws:logs:us-east-1:${var.account_id}:*"
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
          "arn:aws:logs:us-east-1:${var.account_id}:log-group:/aws/lambda/leagueql-sleeper-refresh-${var.environment}:*"
        ]
      },
      {
        Sid    = "QueryDynamoDB"
        Effect = "Allow"
        Action = [
          "dynamodb:Query"
        ]
        Resource = [
          module.dynamodb.primary_table_arn,
          "${module.dynamodb.primary_table_arn}/index/GSI2"
        ]
      },
      {
        Sid    = "InvokeOnboarderLambda"
        Effect = "Allow"
        Action = [
          "lambda:InvokeFunction"
        ]
        Resource = [
          "arn:aws:lambda:us-east-1:${var.account_id}:function:leagueql-onboarder-${var.environment}-east"
        ]
      }
    ]
  })

  tags = {
    environment = var.environment
    project     = "leagueql"
    component   = "data-processing"
    managed-by  = "terraform"
  }
}
