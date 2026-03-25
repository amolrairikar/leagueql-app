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

  # TODO: Figure out how to make this dynamic
  global_secondary_index {
    name               = "GSI1"
    projection_type    = "INCLUDE"
    non_key_attributes = ["seasons", "PK"]
    key_schema {
      attribute_name = "canonical_league_id"
      key_type       = "HASH"
    }
  }

  dynamic "replica" {
    for_each = var.replica_regions
    content {
      region_name                 = replica.value
      point_in_time_recovery      = true
      deletion_protection_enabled = true
      consistency_mode            = "EVENTUAL"
      propagate_tags              = true
    }
  }

  tags = var.tags
}
