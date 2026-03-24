terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      configuration_aliases = [ aws.primary, aws.replica ]
    }
  }
}

locals {
  primary_region = element(split("-", var.primary_aws_region), 1)
  secondary_region = element(split("-", var.secondary_aws_region), 1)
}

resource "aws_s3_bucket" "primary" {
  provider = aws.primary
  bucket   = "${var.bucket_prefix}-${local.primary_region}-${var.account_id}"
  tags     = var.tags
}

resource "aws_s3_bucket_versioning" "primary" {
  provider = aws.primary
  bucket   = aws_s3_bucket.primary.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "primary" {
  provider   = aws.primary
  depends_on = [aws_s3_bucket_versioning.primary]
  bucket     = aws_s3_bucket.primary.id

  dynamic "rule" {
    for_each = var.lifecycle_rules
    content {
      id     = rule.value.rule_name
      status = "Enabled"

      filter {
        prefix = rule.value.prefix
      }

      noncurrent_version_expiration {
        noncurrent_days = rule.value.noncurrent_days
      }

      expiration {
        expired_object_delete_marker = true
      }
    }
  }
}

resource "aws_lambda_permission" "allow_primary_s3" {
  provider      = aws.primary
  statement_id  = "AllowS3Invoke"
  action        = "lambda:InvokeFunction"
  function_name = var.primary_lambda
  principal     = "s3.amazonaws.com"
  source_arn    = aws_s3_bucket.primary.arn
}

resource "aws_s3_bucket_notification" "primary_notification" {
  provider = aws.primary
  bucket   = aws_s3_bucket.primary.id

  lambda_function {
    lambda_function_arn = "arn:aws:lambda:us-east-1:${var.account_id}:function:${var.primary_lambda}"
    events              = ["s3:ObjectCreated:*"]
    filter_prefix       = "raw-api-data/"
  }

  depends_on = [aws_lambda_permission.allow_primary_s3]
}

resource "aws_s3_bucket" "secondary" {
  provider = aws.replica
  bucket   = "${var.bucket_prefix}-${local.secondary_region}-${var.account_id}"
  tags     = var.tags
}

resource "aws_s3_bucket_versioning" "secondary" {
  provider = aws.replica
  bucket   = aws_s3_bucket.secondary.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "secondary" {
  provider   = aws.replica
  depends_on = [aws_s3_bucket_versioning.secondary]
  bucket     = aws_s3_bucket.secondary.id

  dynamic "rule" {
    for_each = var.lifecycle_rules
    content {
      id     = rule.value.rule_name
      status = "Enabled"

      filter {
        prefix = rule.value.prefix
      }

      noncurrent_version_expiration {
        noncurrent_days = rule.value.noncurrent_days
      }

      expiration {
        expired_object_delete_marker = true
      }
    }
  }
}

resource "aws_s3_bucket_replication_configuration" "primary_to_secondary" {
  provider   = aws.primary
  role       = var.replication_role_arn
  bucket     = aws_s3_bucket.primary.id

  depends_on = [
    aws_s3_bucket_versioning.primary,
    aws_s3_bucket_versioning.secondary,
    aws_s3_bucket_lifecycle_configuration.primary,
    aws_s3_bucket_lifecycle_configuration.secondary
  ]

  rule {
    id     = "primary-to-secondary"
    status = "Enabled"

    destination {
      bucket        = aws_s3_bucket.secondary.arn
      storage_class = "STANDARD"
    }

    delete_marker_replication {
      status = "Enabled"
    }

    filter {}
  }
}

resource "aws_s3_bucket_replication_configuration" "secondary_to_primary" {
  provider   = aws.replica
  role       = var.replication_role_arn
  bucket     = aws_s3_bucket.secondary.id

  depends_on = [
    aws_s3_bucket_versioning.primary,
    aws_s3_bucket_versioning.secondary,
    aws_s3_bucket_lifecycle_configuration.primary,
    aws_s3_bucket_lifecycle_configuration.secondary,
    aws_s3_bucket_replication_configuration.primary_to_secondary
  ]

  rule {
    id     = "secondary-to-primary"
    status = "Enabled"

    destination {
      bucket        = aws_s3_bucket.primary.arn
      storage_class = "STANDARD"
    }

    delete_marker_replication {
      status = "Enabled"
    }

    filter {}
  }
}

resource "aws_lambda_permission" "allow_secondary_s3" {
  provider      = aws.replica
  statement_id  = "AllowS3Invoke"
  action        = "lambda:InvokeFunction"
  function_name = var.secondary_lambda
  principal     = "s3.amazonaws.com"
  source_arn    = aws_s3_bucket.secondary.arn
}

resource "aws_s3_bucket_notification" "secondary_notification" {
  provider = aws.replica
  bucket   = aws_s3_bucket.secondary.id

  lambda_function {
    lambda_function_arn = "arn:aws:lambda:us-west-2:${var.account_id}:function:${var.secondary_lambda}"
    events              = ["s3:ObjectCreated:*"]
    filter_prefix       = "raw-api-data/"
  }

  depends_on = [aws_lambda_permission.allow_secondary_s3]
}