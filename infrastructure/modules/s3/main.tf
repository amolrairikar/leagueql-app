terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      configuration_aliases = [ aws.primary, aws.secondary ]
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

resource "aws_s3_bucket" "secondary" {
  provider = aws.secondary
  bucket   = "${var.bucket_prefix}-${local.secondary_region}-${var.account_id}"
  tags     = var.tags
}

resource "aws_s3_bucket_versioning" "secondary" {
  provider = aws.secondary
  bucket   = aws_s3_bucket.secondary.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "secondary" {
  provider   = aws.secondary
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
  provider = aws.primary
  depends_on = [aws_s3_bucket_versioning.primary]

  role   = aws_iam_role.this.arn
  bucket = aws_s3_bucket.primary.id

  rule {
    id     = "primary-to-secondary"
    status = "Enabled"

    destination {
      bucket        = aws_s3_bucket.secondary.arn
      storage_class = "STANDARD"
    }
  }
}

resource "aws_s3_bucket_replication_configuration" "secondary_to_primary" {
  provider = aws.secondary
  depends_on = [aws_s3_bucket_versioning.secondary]

  role   = aws_iam_role.this.arn
  bucket = aws_s3_bucket.secondary.id

  rule {
    id     = "secondary-to-primary"
    status = "Enabled"

    destination {
      bucket        = aws_s3_bucket.primary.arn
      storage_class = "STANDARD"
    }
  }
}

resource "aws_iam_role" "this" {
  provider           = aws.primary
  name               = var.replication_role_name
  description        = var.replication_role_description
  assume_role_policy = file(var.replication_role_trust_policy_file)
  tags               = var.tags
}

resource "aws_iam_role_policy" "this" {
  name   = "${var.replication_role_name}-policy"
  role   = aws_iam_role.this.id
  policy = templatefile(var.replication_role_policy_file, {
    account_id = var.account_id
    region1    = local.primary_region
    region2    = local.secondary_region
  })
}