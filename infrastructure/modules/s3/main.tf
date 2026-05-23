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

  primary_lambda_names = distinct([
    for notification in var.primary_event_notifications :
    element(split(":", notification.lambda_function_arn), length(split(":", notification.lambda_function_arn)) - 1)
  ])

  secondary_lambda_names = distinct([
    for notification in var.secondary_event_notifications :
    element(split(":", notification.lambda_function_arn), length(split(":", notification.lambda_function_arn)) - 1)
  ])
}

resource "aws_s3_bucket" "primary" {
  provider = aws.primary
  bucket   = "${var.bucket_prefix}-${local.primary_region}-${var.account_id}"
  tags     = var.tags
}

resource "aws_s3_bucket_public_access_block" "primary" {
  provider                = aws.primary
  bucket                  = aws_s3_bucket.primary.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_policy" "primary" {
  provider = aws.primary
  bucket   = aws_s3_bucket.primary.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid       = "DenyNonTLS"
        Effect    = "Deny"
        Principal = "*"
        Action    = "s3:*"
        Resource = [
          aws_s3_bucket.primary.arn,
          "${aws_s3_bucket.primary.arn}/*"
        ]
        Condition = {
          Bool = {
            "aws:SecureTransport" = "false"
          }
        }
      }
    ]
  })
  depends_on = [aws_s3_bucket_public_access_block.primary]
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
  for_each = toset(local.primary_lambda_names)

  provider      = aws.primary
  statement_id  = "AllowS3InvokePrimary-${each.value}"
  action        = "lambda:InvokeFunction"
  function_name = each.value
  principal     = "s3.amazonaws.com"
  source_arn    = aws_s3_bucket.primary.arn
}

resource "aws_s3_bucket_notification" "primary_notification" {
  provider = aws.primary
  bucket   = aws_s3_bucket.primary.id

  dynamic "lambda_function" {
    for_each = var.primary_event_notifications
    content {
      lambda_function_arn = lambda_function.value.lambda_function_arn
      events              = lambda_function.value.events
      filter_prefix       = lambda_function.value.filter_prefix
      filter_suffix       = lambda_function.value.filter_suffix
    }
  }

  depends_on = [aws_lambda_permission.allow_primary_s3]
}

resource "aws_s3_bucket" "secondary" {
  provider = aws.replica
  bucket   = "${var.bucket_prefix}-${local.secondary_region}-${var.account_id}"
  tags     = var.tags
}

resource "aws_s3_bucket_public_access_block" "secondary" {
  provider                = aws.replica
  bucket                  = aws_s3_bucket.secondary.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_policy" "secondary" {
  provider = aws.replica
  bucket   = aws_s3_bucket.secondary.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid       = "DenyNonTLS"
        Effect    = "Deny"
        Principal = "*"
        Action    = "s3:*"
        Resource = [
          aws_s3_bucket.secondary.arn,
          "${aws_s3_bucket.secondary.arn}/*"
        ]
        Condition = {
          Bool = {
            "aws:SecureTransport" = "false"
          }
        }
      }
    ]
  })
  depends_on = [aws_s3_bucket_public_access_block.secondary]
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
  for_each = toset(local.secondary_lambda_names)

  provider      = aws.replica
  statement_id  = "AllowS3InvokeSecondary-${each.value}"
  action        = "lambda:InvokeFunction"
  function_name = each.value
  principal     = "s3.amazonaws.com"
  source_arn    = aws_s3_bucket.secondary.arn
}

resource "aws_s3_bucket_notification" "secondary_notification" {
  provider = aws.replica
  bucket   = aws_s3_bucket.secondary.id

  dynamic "lambda_function" {
    for_each = var.secondary_event_notifications
    content {
      lambda_function_arn = lambda_function.value.lambda_function_arn
      events              = lambda_function.value.events
      filter_prefix       = lambda_function.value.filter_prefix
      filter_suffix       = lambda_function.value.filter_suffix
    }
  }

  depends_on = [aws_lambda_permission.allow_secondary_s3]
}