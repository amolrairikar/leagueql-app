terraform {
  required_providers {
    aws = {
      source                = "hashicorp/aws"
      version               = "~> 6.0"
      configuration_aliases = [aws.primary, aws.replica]
    }
  }
}

resource "aws_dynamodb_table" "global_table" {
  provider                    = aws.primary
  name                        = var.table_name
  deletion_protection_enabled = true
  billing_mode                = "PAY_PER_REQUEST"
  hash_key                    = var.hash_key
  range_key                   = var.range_key
  stream_enabled              = true
  stream_view_type            = "NEW_AND_OLD_IMAGES"

  attribute {
    name = var.hash_key
    type = "S"
  }

  attribute {
    name = var.range_key
    type = "S"
  }

  point_in_time_recovery {
    enabled = true
  }

  dynamic "replica" {
    for_each = var.replica_regions
    content {
      region_name                 = replica.value
      point_in_time_recovery      = true
      deletion_protection_enabled = true
      consistency_mode            = "EVENTUAL"
    }
  }

  tags = var.tags
}

resource "aws_dynamodb_tag" "replica_tags" {
  provider     = aws.replica
  resource_arn = replace(aws_dynamodb_table.global_table.arn, data.aws_region.primary.name, var.replica_regions[0])
  depends_on   = [aws_dynamodb_table.global_table]
  
  dynamic "tag" {
    for_each = var.tags
    content {
      key   = tag.key
      value = tag.value
    }
  }
}

# Helper to get the primary region name for the ARN replacement
data "aws_region" "primary" {
  provider = aws.primary
}