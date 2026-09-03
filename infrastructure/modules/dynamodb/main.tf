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

  # JOB_STATUS items carry a Unix-epoch `ttl` so old onboard/refresh/migrate jobs
  # self-clean ~24h after creation. Only items with the attribute are reaped.
  ttl {
    attribute_name = "ttl"
    enabled        = true
  }

  attribute {
    name = "canonical_league_id"
    type = "S"
  }

  attribute {
    name = "platform"
    type = "S"
  }

  attribute {
    name = "league_id"
    type = "S"
  }

  # Only METADATA items carry `onboarded_at`, so GSI3 (below) is effectively a
  # sparse index over METADATA items — the big MATCHUPS/STANDINGS/DRAFT/... items
  # lack this attribute and are omitted from the index.
  attribute {
    name = "onboarded_at"
    type = "S"
  }

  global_secondary_index {
    name               = "GSI1"
    projection_type    = "INCLUDE"
    non_key_attributes = ["seasons", "PK"]
    key_schema {
      attribute_name = "canonical_league_id"
      key_type       = "HASH"
    }
  }

  global_secondary_index {
    name            = "GSI2"
    projection_type = "ALL"
    key_schema {
      attribute_name = "platform"
      key_type       = "HASH"
    }
    key_schema {
      attribute_name = "league_id"
      key_type       = "RANGE"
    }
  }

  # GSI3: sparse index over METADATA items for the leagues-overview dashboard.
  # HASH = SK (constant "METADATA" on these items), RANGE = onboarded_at so a
  # single `SK = "METADATA"` Query returns every league sorted by onboard time,
  # replacing a full-table Scan-with-filter. Only items carrying `onboarded_at`
  # (i.e. METADATA) are indexed. INCLUDE projects the dashboard display fields so
  # the Query needs no follow-up GetItem.
  global_secondary_index {
    name               = "GSI3"
    projection_type    = "INCLUDE"
    non_key_attributes = ["platform", "league_name", "last_refresh_at", "last_accessed_at", "active_platform", "migrated_from", "migrated_at", "owner_user_id"]
    key_schema {
      attribute_name = var.range_key
      key_type       = "HASH"
    }
    key_schema {
      attribute_name = "onboarded_at"
      key_type       = "RANGE"
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
