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
  source           = "../../modules/iam-role"
  role_name        = "leagueql-s3-${var.environment}-replication-role"
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

  # The player stats refresher no longer triggers off player-metadata puts — it runs
  # on a weekly CloudWatch Events schedule as a Fargate task (see BE-011 / regional).
  primary_event_notifications = [
    {
      lambda_function_arn = "arn:aws:lambda:us-east-1:${var.account_id}:function:leagueql-processor-${var.environment}"
      events              = ["s3:ObjectCreated:*"]
      filter_prefix       = "raw-api-data/"
      filter_suffix       = "manifest.json"
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
  source           = "../../modules/iam-role"
  role_name        = "leagueql-${var.environment}-onboarder-role"
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
          "arn:aws:logs:us-east-1:${var.account_id}:log-group:/aws/lambda/leagueql-onboarder-${var.environment}"
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
        # BE-021: the chain Lambdas continue the OTel trace and export to Axiom; the
        # ingest token is a SecureString SSM parameter (set out-of-band, never in TF state).
        Sid    = "ReadAxiomSsmParameter"
        Effect = "Allow"
        Action = [
          "ssm:GetParameter"
        ]
        Resource = [
          "arn:aws:ssm:us-east-1:${var.account_id}:parameter/leagueql/${var.environment}/axiom/api_token",
          "arn:aws:ssm:us-west-2:${var.account_id}:parameter/leagueql/${var.environment}/axiom/api_token"
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
  source           = "../../modules/iam-role"
  role_name        = "leagueql-${var.environment}-onboarding-processor-role"
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
          "arn:aws:logs:us-east-1:${var.account_id}:log-group:/aws/lambda/leagueql-processor-${var.environment}"
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
        # BE-021: the chain Lambdas continue the OTel trace and export to Axiom; the
        # ingest token is a SecureString SSM parameter (set out-of-band, never in TF state).
        Sid    = "ReadAxiomSsmParameter"
        Effect = "Allow"
        Action = [
          "ssm:GetParameter"
        ]
        Resource = [
          "arn:aws:ssm:us-east-1:${var.account_id}:parameter/leagueql/${var.environment}/axiom/api_token",
          "arn:aws:ssm:us-west-2:${var.account_id}:parameter/leagueql/${var.environment}/axiom/api_token"
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
      # BE-022: the processor enqueues a pending-recap marker via dynamodb:PutItem
      # (covered by the DynamoDB write statement above); no ECS/RunTask grant needed.
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
  source           = "../../modules/iam-role"
  role_name        = "leagueql-${var.environment}-sleeper-player-metadata-fetcher-role"
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
          "arn:aws:logs:us-east-1:${var.account_id}:log-group:/aws/lambda/leagueql-sleeper-player-metadata-${var.environment}"
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

# Feature-flag source of truth (BE-017 / FE-026) is an SSM Parameter Store parameter
# named `/leagueql/${var.environment}/feature-flags` in each region (each regional
# API/webhook Lambda reads its own region's copy), holding the flag JSON. Like the
# Stripe/Axiom/Discord SSM values, it is created and edited **out-of-band** in the SSM
# console (a standard-tier `String` — the flags are non-secret booleans) and is never
# managed in TF, so a toggle never needs a `terraform apply`. The Lambda code reads
# all flags off when the parameter is missing, so a fresh environment is safe until the
# value is set. Only the read grant lives in TF (below).

module "api-lambda-role" {
  source           = "../../modules/iam-role"
  role_name        = "leagueql-${var.environment}-api-role"
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
          "arn:aws:logs:us-east-1:${var.account_id}:log-group:/aws/lambda/leagueql-api-${var.environment}-east",
          "arn:aws:logs:us-west-2:${var.account_id}:log-group:/aws/lambda/leagueql-api-${var.environment}-west"
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
      },
      {
        # BE-015: the checkout / billing-portal endpoints need the Stripe secret
        # key, stored as a SecureString SSM parameter (set out-of-band, never in
        # TF state). The API does not read the webhook signing secret.
        Sid    = "ReadStripeSsmParameters"
        Effect = "Allow"
        Action = [
          "ssm:GetParameter"
        ]
        Resource = [
          "arn:aws:ssm:us-east-1:${var.account_id}:parameter/leagueql/${var.environment}/stripe/secret_key",
          "arn:aws:ssm:us-west-2:${var.account_id}:parameter/leagueql/${var.environment}/stripe/secret_key"
        ]
      },
      {
        # BE-020: the API Lambda exports OpenTelemetry traces to Axiom; the ingest
        # token is a SecureString SSM parameter (set out-of-band, never in TF state).
        Sid    = "ReadAxiomSsmParameter"
        Effect = "Allow"
        Action = [
          "ssm:GetParameter"
        ]
        Resource = [
          "arn:aws:ssm:us-east-1:${var.account_id}:parameter/leagueql/${var.environment}/axiom/api_token",
          "arn:aws:ssm:us-west-2:${var.account_id}:parameter/leagueql/${var.environment}/axiom/api_token"
        ]
      },
      {
        # BE-017: feature flags are resolved at runtime from an SSM Parameter Store
        # parameter (IAM-role access, no secret). The parameter is set out-of-band in
        # the SSM console, never in TF state. Grant read on both regions' copy.
        Sid    = "ReadFeatureFlagsSsmParameter"
        Effect = "Allow"
        Action = [
          "ssm:GetParameter"
        ]
        Resource = [
          "arn:aws:ssm:us-east-1:${var.account_id}:parameter/leagueql/${var.environment}/feature-flags",
          "arn:aws:ssm:us-west-2:${var.account_id}:parameter/leagueql/${var.environment}/feature-flags"
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

module "stripe-webhook-lambda-role" {
  source           = "../../modules/iam-role"
  role_name        = "leagueql-${var.environment}-stripe-webhook-role"
  role_description = "Execution role for the Stripe billing webhook lambda."
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
          "arn:aws:logs:us-east-1:${var.account_id}:log-group:/aws/lambda/leagueql-stripe-webhook-${var.environment}-east",
          "arn:aws:logs:us-west-2:${var.account_id}:log-group:/aws/lambda/leagueql-stripe-webhook-${var.environment}-west"
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
          "arn:aws:logs:us-east-1:${var.account_id}:log-group:/aws/lambda/leagueql-stripe-webhook-${var.environment}-east:*",
          "arn:aws:logs:us-west-2:${var.account_id}:log-group:/aws/lambda/leagueql-stripe-webhook-${var.environment}-west:*"
        ]
      },
      {
        Sid    = "ReadWriteDynamoDB"
        Effect = "Allow"
        Action = [
          "dynamodb:GetItem",
          "dynamodb:PutItem",
          "dynamodb:UpdateItem"
        ]
        Resource = [
          module.dynamodb.primary_table_arn,
          module.dynamodb.replica_table_arn
        ]
      },
      {
        # BE-015: Stripe secret key + webhook signing secret live as SecureString
        # SSM parameters (set out-of-band, never in TF state). Grant read on both
        # regions' copies; the value is fetched by the Lambda at cold start.
        Sid    = "ReadStripeSsmParameters"
        Effect = "Allow"
        Action = [
          "ssm:GetParameter"
        ]
        Resource = [
          "arn:aws:ssm:us-east-1:${var.account_id}:parameter/leagueql/${var.environment}/stripe/secret_key",
          "arn:aws:ssm:us-west-2:${var.account_id}:parameter/leagueql/${var.environment}/stripe/secret_key",
          "arn:aws:ssm:us-east-1:${var.account_id}:parameter/leagueql/${var.environment}/stripe/webhook_secret",
          "arn:aws:ssm:us-west-2:${var.account_id}:parameter/leagueql/${var.environment}/stripe/webhook_secret"
        ]
      },
      {
        # BE-017: the webhook reads the global `billing` flag from the SSM
        # feature-flag parameter (set out-of-band, never in TF state) to no-op when
        # billing is off. Same source as the API.
        Sid    = "ReadFeatureFlagsSsmParameter"
        Effect = "Allow"
        Action = [
          "ssm:GetParameter"
        ]
        Resource = [
          "arn:aws:ssm:us-east-1:${var.account_id}:parameter/leagueql/${var.environment}/feature-flags",
          "arn:aws:ssm:us-west-2:${var.account_id}:parameter/leagueql/${var.environment}/feature-flags"
        ]
      },
      {
        # BE-021: the webhook is now a traced Lambda and exports OTel spans to Axiom;
        # the ingest token is a SecureString SSM parameter (set out-of-band, never in
        # TF state). Grant read on both regions' copies.
        Sid    = "ReadAxiomSsmParameter"
        Effect = "Allow"
        Action = [
          "ssm:GetParameter"
        ]
        Resource = [
          "arn:aws:ssm:us-east-1:${var.account_id}:parameter/leagueql/${var.environment}/axiom/api_token",
          "arn:aws:ssm:us-west-2:${var.account_id}:parameter/leagueql/${var.environment}/axiom/api_token"
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

# Execution role for the AI weekly matchup recap generator (BE-022). Reads the
# matchup/standings views, writes recap items, reads feature flags + the Axiom token
# from SSM, and invokes the Bedrock Haiku 4.5 inference profile (us-east-1).
# AI weekly matchup recaps via Bedrock batch inference (BE-022): the drainer Lambda
# (scheduled) submits jobs and the completion Lambda (EventBridge on job state change)
# writes the results. Three roles: the two Lambda execution roles + the Bedrock batch
# service role Bedrock assumes to read input / write output in S3.

# Drainer Lambda role — enumerates the queue + views, builds batch input, submits the
# Bedrock job, writes the manifest, flips markers.
module "recap-drainer-role" {
  source           = "../../modules/iam-role"
  role_name        = "leagueql-${var.environment}-recap-drainer-role"
  role_description = "Execution role for the AI weekly matchup recap drainer Lambda."
  trust_policy_json = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action    = "sts:AssumeRole"
        Effect    = "Allow"
        Principal = { Service = "lambda.amazonaws.com" }
      }
    ]
  })
  role_policy_json = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "WriteLambdaLogGroup"
        Effect = "Allow"
        Action = ["logs:CreateLogGroup"]
        Resource = [
          "arn:aws:logs:us-east-1:${var.account_id}:log-group:/aws/lambda/leagueql-recap-drainer-${var.environment}"
        ]
      },
      {
        Sid    = "WriteLambdaLogs"
        Effect = "Allow"
        Action = ["logs:CreateLogStream", "logs:PutLogEvents"]
        Resource = [
          "arn:aws:logs:us-east-1:${var.account_id}:log-group:/aws/lambda/leagueql-recap-drainer-${var.environment}:*"
        ]
      },
      {
        Sid    = "ReadWriteDynamoDB"
        Effect = "Allow"
        Action = [
          "dynamodb:GetItem",
          "dynamodb:Query",
          "dynamodb:PutItem",
          "dynamodb:UpdateItem",
          "dynamodb:DeleteItem",
          "dynamodb:BatchGetItem"
        ]
        Resource = [
          module.dynamodb.primary_table_arn,
          "${module.dynamodb.primary_table_arn}/index/GSI1"
        ]
      },
      {
        # Batch input JSONL lands here; Bedrock reads it via the batch service role.
        Sid    = "WriteBatchInput"
        Effect = "Allow"
        Action = ["s3:PutObject", "s3:GetObject"]
        Resource = [
          "arn:aws:s3:::leagueql-recap-batch-${var.environment}-${var.account_id}/*"
        ]
      },
      {
        # BE-022: submit + inspect Bedrock batch inference jobs (separate quota lane).
        Sid    = "ManageBedrockBatchJobs"
        Effect = "Allow"
        Action = [
          "bedrock:CreateModelInvocationJob",
          "bedrock:GetModelInvocationJob",
          "bedrock:ListModelInvocationJobs"
        ]
        Resource = "*"
      },
      {
        # PassRole so Bedrock can assume the batch service role for the job's S3 I/O.
        Sid      = "PassBedrockBatchRole"
        Effect   = "Allow"
        Action   = ["iam:PassRole"]
        Resource = [module.recap-batch-service-role.role_arn]
      },
      {
        # BE-022: first-run self-subscribe to the Llama 3.3 70B Bedrock Marketplace
        # product (account-wide, one-time). Drop once an admin subscribes out-of-band.
        Sid      = "BedrockMarketplaceSubscribe"
        Effect   = "Allow"
        Action   = ["aws-marketplace:Subscribe", "aws-marketplace:ViewSubscriptions"]
        Resource = "*"
      },
      {
        # BE-017: premium gate reads the global billing / premium_feature flags.
        Sid    = "ReadFeatureFlagsSsmParameter"
        Effect = "Allow"
        Action = ["ssm:GetParameter"]
        Resource = [
          "arn:aws:ssm:us-east-1:${var.account_id}:parameter/leagueql/${var.environment}/feature-flags"
        ]
      },
      {
        # BE-021: export OTel spans to Axiom; token is a SecureString SSM parameter.
        Sid    = "ReadAxiomSsmParameter"
        Effect = "Allow"
        Action = ["ssm:GetParameter"]
        Resource = [
          "arn:aws:ssm:us-east-1:${var.account_id}:parameter/leagueql/${var.environment}/axiom/api_token"
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

# Completion Lambda role — reads finished jobs' output from S3 and writes recaps.
module "recap-completion-role" {
  source           = "../../modules/iam-role"
  role_name        = "leagueql-${var.environment}-recap-completion-role"
  role_description = "Execution role for the AI weekly matchup recap completion Lambda."
  trust_policy_json = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action    = "sts:AssumeRole"
        Effect    = "Allow"
        Principal = { Service = "lambda.amazonaws.com" }
      }
    ]
  })
  role_policy_json = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "WriteLambdaLogGroup"
        Effect = "Allow"
        Action = ["logs:CreateLogGroup"]
        Resource = [
          "arn:aws:logs:us-east-1:${var.account_id}:log-group:/aws/lambda/leagueql-recap-completion-${var.environment}"
        ]
      },
      {
        Sid    = "WriteLambdaLogs"
        Effect = "Allow"
        Action = ["logs:CreateLogStream", "logs:PutLogEvents"]
        Resource = [
          "arn:aws:logs:us-east-1:${var.account_id}:log-group:/aws/lambda/leagueql-recap-completion-${var.environment}:*"
        ]
      },
      {
        Sid    = "ReadWriteDynamoDB"
        Effect = "Allow"
        Action = [
          "dynamodb:GetItem",
          "dynamodb:PutItem",
          "dynamodb:UpdateItem",
          "dynamodb:DeleteItem"
        ]
        Resource = [module.dynamodb.primary_table_arn]
      },
      {
        Sid    = "ReadBatchOutput"
        Effect = "Allow"
        Action = ["s3:GetObject", "s3:ListBucket"]
        Resource = [
          "arn:aws:s3:::leagueql-recap-batch-${var.environment}-${var.account_id}",
          "arn:aws:s3:::leagueql-recap-batch-${var.environment}-${var.account_id}/*"
        ]
      },
      {
        # Alert on a failed/expired batch job.
        Sid      = "PublishSNSFailureAlerts"
        Effect   = "Allow"
        Action   = ["sns:Publish"]
        Resource = ["arn:aws:sns:us-east-1:${var.account_id}:leagueql-lambda-alerts-${var.environment}-east"]
      },
      {
        Sid    = "ReadAxiomSsmParameter"
        Effect = "Allow"
        Action = ["ssm:GetParameter"]
        Resource = [
          "arn:aws:ssm:us-east-1:${var.account_id}:parameter/leagueql/${var.environment}/axiom/api_token"
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

# Bedrock batch service role — Bedrock assumes this to read the input JSONL and write
# the output JSONL in the batch bucket (passed as the job's roleArn).
module "recap-batch-service-role" {
  source           = "../../modules/iam-role"
  role_name        = "leagueql-${var.environment}-recap-batch-role"
  role_description = "Service role Bedrock assumes for recap batch inference S3 I/O."
  trust_policy_json = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action    = "sts:AssumeRole"
        Effect    = "Allow"
        Principal = { Service = "bedrock.amazonaws.com" }
        Condition = {
          StringEquals = { "aws:SourceAccount" = var.account_id }
        }
      }
    ]
  })
  role_policy_json = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "ReadWriteBatchIO"
        Effect = "Allow"
        Action = ["s3:GetObject", "s3:PutObject", "s3:ListBucket"]
        Resource = [
          "arn:aws:s3:::leagueql-recap-batch-${var.environment}-${var.account_id}",
          "arn:aws:s3:::leagueql-recap-batch-${var.environment}-${var.account_id}/*"
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

# Execution role for the SNS-to-Discord alert forwarder. It only consumes SNS (no
# sns:Publish) and reads the Discord webhook URL from a SecureString SSM parameter.
module "discord-notifier-lambda-role" {
  source           = "../../modules/iam-role"
  role_name        = "leagueql-${var.environment}-discord-notifier-role"
  role_description = "Execution role for the SNS-to-Discord alert forwarder lambda."
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
          "arn:aws:logs:us-east-1:${var.account_id}:log-group:/aws/lambda/leagueql-discord-notifier-${var.environment}-east",
          "arn:aws:logs:us-west-2:${var.account_id}:log-group:/aws/lambda/leagueql-discord-notifier-${var.environment}-west"
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
          "arn:aws:logs:us-east-1:${var.account_id}:log-group:/aws/lambda/leagueql-discord-notifier-${var.environment}-east:*",
          "arn:aws:logs:us-west-2:${var.account_id}:log-group:/aws/lambda/leagueql-discord-notifier-${var.environment}-west:*"
        ]
      },
      {
        # The Discord webhook URL lives as a SecureString SSM parameter (set
        # out-of-band, never in TF state). Grant read on both regions' copies; the
        # value is fetched by the Lambda at cold start.
        Sid    = "ReadDiscordWebhookSsmParameter"
        Effect = "Allow"
        Action = [
          "ssm:GetParameter"
        ]
        Resource = [
          "arn:aws:ssm:us-east-1:${var.account_id}:parameter/leagueql/${var.environment}/discord/webhook_url",
          "arn:aws:ssm:us-west-2:${var.account_id}:parameter/leagueql/${var.environment}/discord/webhook_url"
        ]
      }
    ]
  })

  tags = {
    environment = var.environment
    project     = "leagueql"
    component   = "monitoring"
    managed-by  = "terraform"
  }
}

module "api-gateway-role" {
  source           = "../../modules/iam-role"
  role_name        = "leagueql-api-gateway-${var.environment}-role"
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
          "arn:aws:logs:us-east-1:${var.account_id}:log-group:/aws/apigateway/leagueql-api-${var.environment}-east",
          "arn:aws:logs:us-west-2:${var.account_id}:log-group:/aws/apigateway/leagueql-api-${var.environment}-west"
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

# Container image for the Sleeper player stats refresher Fargate task. Pushed by CI
# (deploy-fargate-image) before the regional task definition references it.
resource "aws_ecr_repository" "sleeper_player_stats_refresher" {
  provider             = aws.primary
  name                 = "leagueql-sleeper-player-stats-refresher-${var.environment}"
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }

  tags = {
    environment = var.environment
    project     = "leagueql"
    component   = "data-processing"
    managed-by  = "terraform"
  }
}

resource "aws_ecr_lifecycle_policy" "sleeper_player_stats_refresher" {
  provider   = aws.primary
  repository = aws_ecr_repository.sleeper_player_stats_refresher.name

  policy = jsonencode({
    rules = [
      {
        rulePriority = 1
        description  = "Keep only the last 10 images"
        selection = {
          tagStatus   = "any"
          countType   = "imageCountMoreThan"
          countNumber = 10
        }
        action = {
          type = "expire"
        }
      }
    ]
  })
}

# Task role — the application identity the container assumes at runtime. Repurposed
# from the former Lambda execution role: trust is now ecs-tasks (not lambda) and the
# log-group statements are dropped (the execution role + Terraform-created log group
# handle logging). The S3 read/write statements are unchanged.
module "sleeper-player-stats-refresher-task-role" {
  source           = "../../modules/iam-role"
  role_name        = "leagueql-${var.environment}-sleeper-player-stats-refresher-task-role"
  role_description = "Task role for Sleeper player stats refresher Fargate task."
  trust_policy_json = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ecs-tasks.amazonaws.com"
        }
      }
    ]
  })
  role_policy_json = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        # Required so a GetObject on a not-yet-existing stats cache returns 404
        # NoSuchKey (handled as a fresh-start bootstrap) rather than 403 AccessDenied.
        Sid    = "ListBucket"
        Effect = "Allow"
        Action = [
          "s3:ListBucket"
        ]
        Resource = [
          local.primary_bucket_arn
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
          "s3:PutObject",
          "s3:GetObject"
        ]
        Resource = [
          "${local.primary_bucket_arn}/player-stats/sleeper_nfl_player_stats.json"
        ]
      },
      {
        # GetObject (not just PutObject) so the deep-merge read of the test key works
        # when the object already exists; ListBucket above covers the missing case.
        Sid    = "ReadWriteTestPlayerStats"
        Effect = "Allow"
        Action = [
          "s3:PutObject",
          "s3:GetObject"
        ]
        Resource = [
          "${local.primary_bucket_arn}/player-stats/integration-test/sleeper_nfl_player_stats.json"
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

# Execution role — used by the ECS agent (not the app) to pull the image from ECR
# and ship container logs to the task's CloudWatch log group.
module "sleeper-stats-task-exec-role" {
  source           = "../../modules/iam-role"
  role_name        = "leagueql-${var.environment}-sleeper-stats-task-exec-role"
  role_description = "Execution role for the Sleeper player stats refresher Fargate task."
  trust_policy_json = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ecs-tasks.amazonaws.com"
        }
      }
    ]
  })
  role_policy_json = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid      = "ECRAuthToken"
        Effect   = "Allow"
        Action   = ["ecr:GetAuthorizationToken"]
        Resource = "*"
      },
      {
        Sid    = "ECRPull"
        Effect = "Allow"
        Action = [
          "ecr:BatchCheckLayerAvailability",
          "ecr:GetDownloadUrlForLayer",
          "ecr:BatchGetImage"
        ]
        Resource = [
          aws_ecr_repository.sleeper_player_stats_refresher.arn
        ]
      },
      {
        Sid    = "WriteTaskLogs"
        Effect = "Allow"
        Action = [
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = [
          "arn:aws:logs:us-east-1:${var.account_id}:log-group:/ecs/leagueql-sleeper-player-stats-refresher-${var.environment}:*"
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

# Invoke role assumed by the CloudWatch Events rule to launch the scheduled task.
module "sleeper-stats-events-role" {
  source           = "../../modules/iam-role"
  role_name        = "leagueql-${var.environment}-sleeper-stats-events-role"
  role_description = "Role assumed by EventBridge to run the Sleeper player stats refresher task."
  trust_policy_json = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "events.amazonaws.com"
        }
      }
    ]
  })
  role_policy_json = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid      = "RunTask"
        Effect   = "Allow"
        Action   = ["ecs:RunTask"]
        Resource = ["arn:aws:ecs:us-east-1:${var.account_id}:task-definition/leagueql-sleeper-player-stats-refresher-${var.environment}:*"]
      },
      {
        Sid    = "PassTaskRoles"
        Effect = "Allow"
        Action = ["iam:PassRole"]
        Resource = [
          module.sleeper-player-stats-refresher-task-role.role_arn,
          module.sleeper-stats-task-exec-role.role_arn
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
  source           = "../../modules/iam-role"
  role_name        = "leagueql-${var.environment}-sleeper-league-refresh-role"
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
          "arn:aws:logs:us-east-1:${var.account_id}:log-group:/aws/lambda/leagueql-sleeper-refresh-${var.environment}"
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
        # BE-021: the chain Lambdas continue the OTel trace and export to Axiom; the
        # ingest token is a SecureString SSM parameter (set out-of-band, never in TF state).
        Sid    = "ReadAxiomSsmParameter"
        Effect = "Allow"
        Action = [
          "ssm:GetParameter"
        ]
        Resource = [
          "arn:aws:ssm:us-east-1:${var.account_id}:parameter/leagueql/${var.environment}/axiom/api_token",
          "arn:aws:ssm:us-west-2:${var.account_id}:parameter/leagueql/${var.environment}/axiom/api_token"
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
