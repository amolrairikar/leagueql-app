# Cloudflare edge workers backing the landing-page league count (backend/app-stats-league-count):
#   - get-counts:  serves GET /counts on api.leagueql.com from the COUNTS_KV namespace
#   - sync-counts: hourly cron that counts league METADATA items in DynamoDB (GSI3) and
#                  writes the result to COUNTS_KV
# Prod-only: the route and table are prod resources, so there is no dev counterpart.
#
# Worker code is bundled by wrangler (`npm run build` in workers/<name>, a --dry-run deploy
# that writes dist/index.js) and uploaded here; wrangler itself never deploys these workers.

terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
    cloudflare = {
      source  = "cloudflare/cloudflare"
      version = "~> 5.28"
    }
  }
}

provider "aws" {
  region = "us-east-1"
}

# Authenticates via the CLOUDFLARE_API_TOKEN environment variable.
provider "cloudflare" {}

locals {
  workers_dir = "${path.module}/../../workers"

  get_counts_bundle  = "${local.workers_dir}/get-counts/dist/index.js"
  sync_counts_bundle = "${local.workers_dir}/sync-counts/dist/index.js"

  observability = {
    enabled = true
    logs = {
      enabled         = true
      invocation_logs = true
    }
  }
}

data "cloudflare_zone" "leagueql" {
  filter = {
    name = var.zone_name
  }
}

# ── KV ───────────────────────────────────────────────────────────────────────

resource "cloudflare_workers_kv_namespace" "counts" {
  account_id = var.cloudflare_account_id
  title      = "COUNTS_KV"

  lifecycle {
    prevent_destroy = true
  }
}

# ── get-counts ───────────────────────────────────────────────────────────────

resource "cloudflare_workers_script" "get_counts" {
  account_id         = var.cloudflare_account_id
  script_name        = "get-counts"
  main_module        = "index.js"
  content_file       = local.get_counts_bundle
  content_sha256     = filesha256(local.get_counts_bundle)
  compatibility_date = "2024-01-01"

  bindings = [
    {
      name         = "COUNTS_KV"
      type         = "kv_namespace"
      namespace_id = cloudflare_workers_kv_namespace.counts.id
    },
  ]

  observability = local.observability
}

resource "cloudflare_workers_route" "counts" {
  zone_id = data.cloudflare_zone.leagueql.zone_id
  pattern = "api.${var.zone_name}/counts"
  script  = cloudflare_workers_script.get_counts.script_name
}

# ── sync-counts ──────────────────────────────────────────────────────────────

resource "cloudflare_workers_script" "sync_counts" {
  account_id          = var.cloudflare_account_id
  script_name         = "sync-counts"
  main_module         = "index.js"
  content_file        = local.sync_counts_bundle
  content_sha256      = filesha256(local.sync_counts_bundle)
  compatibility_date  = "2024-01-01"
  compatibility_flags = ["nodejs_compat"]

  bindings = [
    {
      name         = "COUNTS_KV"
      type         = "kv_namespace"
      namespace_id = cloudflare_workers_kv_namespace.counts.id
    },
    {
      name = "AWS_REGION"
      type = "plain_text"
      text = "us-east-1"
    },
    {
      name = "DYNAMODB_TABLE"
      type = "plain_text"
      text = "leagueql-table-prod"
    },
    {
      name = "AWS_ACCESS_KEY_ID"
      type = "secret_text"
      text = aws_iam_access_key.sync_counts.id
    },
    {
      name = "AWS_SECRET_ACCESS_KEY"
      type = "secret_text"
      text = aws_iam_access_key.sync_counts.secret
    },
  ]

  observability = local.observability
}

resource "cloudflare_workers_cron_trigger" "sync_counts" {
  account_id  = var.cloudflare_account_id
  script_name = cloudflare_workers_script.sync_counts.script_name
  schedules = [
    { cron = "0 * * * *" }, # every hour
  ]
}

# ── AWS credentials for sync-counts ──────────────────────────────────────────
# Cloudflare Workers can't assume an IAM role, so sync-counts uses a long-lived access key.
# The IAM user and its policy (Query on the prod table's GSI3 only) are owned by the separate
# account-setup Terraform project; only the key lives here so it can be wired straight into
# the worker's secret bindings.
# Rotate with: terraform apply -replace=aws_iam_access_key.sync_counts

resource "aws_iam_access_key" "sync_counts" {
  user = "leagueql-user"
}
